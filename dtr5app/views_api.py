import json
from datetime import date

import base64
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse, Http404
from django.http.response import HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from os import remove
from os.path import join
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from dtr5app.models import Visit, Sr, Flag, PushNotificationEndpoint, Message, \
    Subscribed
from dtr5app.serializers import SubscribedSerializer, \
    AuthUserSerializer, BasicUserSerializer, ViewUserSerializer, \
    ViewSrSerializer, MessageSerializer
from dtr5app.templatetags.dtr5tags import prefdist
from dtr5app.utils import add_likes_sent, add_likes_recv, \
    add_matches_to_user_list, add_auth_user_latlng, \
    get_user_and_related_or_404, get_user_list_from_username_list, \
    get_user_list_after, get_prevnext_user, prepare_paginated_user_list, \
    get_paginated_user_list, get_matches_user_list, count_matches, \
    update_list_of_subscribed_subreddits
from dtr5app.utils_push_notifications import simple_push_notification
from dtr5app.utils_search import search_results_buffer, update_search_settings,\
    search_subreddit_users
from simple_reddit_oauth import api
from toolbox import force_int


@require_http_methods(["GET"])
def filter_members_view(request):
    # TODO: use DRF here.
    """
    Receives a list of Reddit usernames and returns a list of Reddmeet users
    with some basic data for each.

    Used by the reddmeet-chrome-extension
    """
    usernames = request.GET.get('userlist', None).split(' ')

    if not usernames:
        return JsonResponse([])

    # Verify that userlist only contains valid usernames and limit it to not
    # more than 200 items (the number of comments shows per thread for users
    # with no Reddit Gold).
    usernames = [x for x in usernames if settings.RE_USERNAME.match(x)][:200]

    # Fetch a list of all of them and return a list of usernames found with
    # attached additional data (pic, etc).
    ul = User.objects.filter(username__in=usernames)\
                     .prefetch_related('profile')[:50]

    if request.user.is_authenticated():
        ul = add_likes_sent(ul, request.user)
        ul = add_likes_recv(ul, request.user)
        ul = add_matches_to_user_list(ul, request.user)
        ul = add_auth_user_latlng(request.user, ul)

    response_data = []
    for user in ul:
        item = {'name': user.username,
                'pic': user.profile.pics[0]['url'] if user.profile.pics else '',
                'sex_symbol': user.profile.get_sex_symbol(),
                'sex': user.profile.get_sex_display(),
                'age': user.profile.get_age(), }

        if request.user.is_authenticated():
            item['is_like_sent'] = user.is_like_sent
            item['is_like_recv'] = user.is_like_recv
            item['is_match'] = user.is_match
            item['dist'] = prefdist(user.profile.get_distance(), request.user)

        response_data.append(item)

    return JsonResponse({'userlist': response_data})


# noinspection PyUnusedLocal
@api_view(['GET', ])
def sr_user_list(request, sr, format=None):
    """Return a list of users who are member of a subreddit."""
    pg = int(request.GET.get('page', 1))
    view_sr = get_object_or_404(Sr, display_name__iexact=sr)

    # Only allow a selected number of Subreddits to be views publicly.
    if request.user.is_anonymous() and not view_sr.display_name.lower() in \
            [x.lower() for x in settings.SR_ANON_ACCESS_ALLOWED]:
        return Response(status.HTTP_401_UNAUTHORIZED)

    # Filter displayed members: normalize search options.
    params = dict()
    params['order'] = request.GET.get('order', '-last_login')
    params['has_verified_email'] = \
        bool(force_int(request.GET.get('has_verified_email', 0)))
    params['hide_no_pic'] = bool(force_int(request.GET.get('hide_no_pic', 1)))
    params['sex'] = force_int(request.GET.get('s', 0))
    params['distance'] = force_int(request.GET.get('dist', 1))
    params['minage'] = force_int(request.GET.get('minage', 18))
    if params['minage'] not in range(18, 100):
        params['minage'] = 18
    params['maxage'] = force_int(request.GET.get('maxage', 100))
    if params['maxage'] not in range(params['minage'], 101):
        params['maxage'] = 100
    if request.user.is_authenticated():
        params['user_id'] = request.user.id
        params['lat'] = request.user.profile.lat
        params['lng'] = request.user.profile.lng

    # Fetch users and order them.
    ul = search_subreddit_users(params, view_sr)
    if params['order'] == '-accessed':  # most recently accessed first
        ul = ul.order_by('-profile__accessed')
    elif params['order'] == '-date_joined':  # most recent redddate acccount
        ul = ul.order_by('-date_joined')
    elif params['order'] == '-views_count':  # most views first
        ul = ul.order_by('-profile__views_count')

    # Paginate and add "is_like_recv" and "is_like"sent"
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    return Response(data={
        'user_list': BasicUserSerializer(ul.object_list, many=True).data,
        'view_sr': ViewSrSerializer(view_sr, many=False).data})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def search_params(request):
    """
    Save the user search settings and redirect to search results page.
    """
    # TODO: Remove this step, update user search options from GET request
    # TODO: only when they have changed.
    if settings.DEBUG:
        print('# POST sr-fav     == {}'.format(request.POST.get('sr-fav')))
        print('# POST f_distance == {}'.format(request.POST.get('f_distance')))
        print('# POST f_sex      == {}'.format(request.POST.get('f_sex')))
        print('# POST order_by   == {}'.format(request.POST.get('order_by')))

    # Save search options from request.POST
    update_search_settings(request)
    # Then force a search results buffer refresh
    search_results_buffer(request, force=True)
    # If no profiles found, return a 404 from here
    if len(request.session['search_results_buffer']) < 1:
        return HttpResponseNotFound()  # 404
    # Otherwise return Found
    return JsonResponse({})  # HTTP 200


# noinspection PyUnusedLocal
@csrf_exempt
@login_required
@api_view(['GET', 'HEAD', 'OPTIONS'])
def results_list(request, format=None):
    """
    Return a list of search results from auth user's search buffer.

    On POST request, update the search settings before returning the results
    list.
    """
    pg = int(request.GET.get('page', 1))
    if pg == 1:
        update_search_if_changed(request.GET, request.user, request.session)
        search_results_buffer(request, force=True)
    else:
        search_results_buffer(request)

    ul = request.session['search_results_buffer']
    ul = prepare_paginated_user_list(ul, pg)

    ul.object_list = get_user_list_from_username_list(ul.object_list)
    ul.object_list = add_auth_user_latlng(request.user, ul.object_list)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)

    return Response(data={
        'count': ul.paginator.count,
        'num_pages': ul.paginator.num_pages,
        'user_list': BasicUserSerializer(ul.object_list, many=True).data,
    })


# noinspection PyUnusedLocal
@login_required
@api_view(['GET', ])
def user_detail(request, username, format=None):
    """
    Display one user profile, enhanced with additional data about the
    relationship between thise user and the authenticated user, for example
    the if one "like" or "nope" the other, the distance between them, etc.

    If auth user is viewing their own profile, return some additional data
    from the Profile that should only be viewable by the owning user or a
    staff user.
    """
    view_user = get_user_and_related_or_404(username, 'profile', 'subs')

    if not view_user.is_active:
        # return HttpResponseNotFound('user was banned')
        return Response(status=status.HTTP_404_NOT_FOUND)
    if not view_user.last_login:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat,
                                        request.user.profile.lng)

    # Make sure there is a list of 10 pic objects, empty or not.
    setattr(view_user, 'pics_list', view_user.profile.pics[:10])
    view_user.pics_list += [None] * (10 - len(view_user.pics_list))

    # Get the next five users to be displayed at the end of the profile page.
    search_results_buffer(request)
    user_list = get_user_list_after(request, view_user, 5)

    # Find previous and next user on the list, relative to view user.
    prev_user, next_user = get_prevnext_user(request, view_user)
    if not prev_user and user_list:
        prev_user = user_list[-1]
    if not next_user and user_list:
        next_user = user_list[0]

    # Count the profile view, unless auth user is viewing their own profile.
    if request.user.pk != view_user.pk:
        # to minimize repeated counting (in case of page relaod etc) remember
        # the last 10 profiles authuser visited and don't count them again.
        if 'last_viewed_users' not in request.session.keys():
            request.session['last_viewed_users'] = []
        try:
            request.session['last_viewed_users'].remove(view_user.pk)
        except ValueError:
            view_user.profile.views_count += 1
            view_user.profile.new_views_count += 1
            view_user.profile.save(update_fields=['views_count',
                                                  'new_views_count'])
        request.session['last_viewed_users'].append(view_user.pk)

        # remember the view for visitor history
        Visit.add_visitor_host(request.user, view_user)

    # there was an error with the "created" timestamp handling, so some were
    # set to "0", i.e. Epoch time 1970-01-01. Filter those out.
    show_created = (view_user.profile.created and
                    view_user.profile.created > date(1970, 1, 1))

    # The relation data between auth_user and view_user should NOT be part
    # of the User model instance, but should live outside of it.
    return Response(data={
        'show_created': show_created,
        'view_user': ViewUserSerializer(view_user).data,
        'prev_user': BasicUserSerializer(prev_user).data,
        'next_user': BasicUserSerializer(next_user).data,
        'user_list': BasicUserSerializer(user_list, many=True).data,
        'common_subs': SubscribedSerializer(
            view_user.profile.get_common_subs(request.user), many=True).data,
        'not_common_subs': SubscribedSerializer(
            view_user.profile.get_not_common_subs(request.user), many=True).data,
        'is_match': request.user.profile.match_with(view_user),
        'is_like': request.user.profile.does_like(view_user),
        'is_nope': request.user.profile.does_nope(view_user), })


# noinspection PyUnusedLocal
@login_required()
@api_view(['GET', 'PATCH', 'PUT', 'DELETE'])
def authuser_detail(request, format=None):
    if request.method == 'GET':
        data = AuthUserSerializer(request.user).data
        return Response(data={'authuser': data})

    if request.method == 'DELETE':
        # TODO: implement DELETE auth user model.
        return Response(status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        serializer = AuthUserSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PATCH':
        pass  # TODO: implement PATCHing auth user model, then remove PUT.


# noinspection PyUnusedLocal
@login_required()
@api_view(['GET', 'PUT'])
def authuser_subs(request, format=None):
    if request.method == 'PUT':
        # Update subreddit list from Reddit before returning subs list.
        subscribed = api.get_sr_subscriber(request, settings.SR_FETCH_LIMIT)
        if subscribed:
            update_list_of_subscribed_subreddits(request.user, subscribed)

    sr_li = SubscribedSerializer(request.user.subs, many=True).data
    return Response(data={'subs': sr_li})


# noinspection PyUnusedLocal
@login_required()
@api_view(['PUT', 'DELETE'])
def authuser_picture(request, format=None):
    """Upload JSON data with a base64 encoded file of auth user, already with
    correct dimensions (resized on client) and store it to "avatars/m" under
    auth user's username"""
    fonly = '{}.jpg'.format(request.user.username)
    fname = join(settings.BASE_DIR, 'avatars/m', fonly)

    if request.method == 'PUT':
        data = json.loads(request.body.decode('utf-8'))
        b64 = data['pic']['dataURL'].split(',', 1)[1].encode('ascii')
        b64fix = b64 + (b'=' * (4 - len(b64) % 4))  # correct padding!
        img = base64.urlsafe_b64decode(b64fix)

        with open(fname, 'wb') as fh:
            fh.write(img)

    elif request.method == 'DELETE':
        try:
            remove(fname)
        except FileNotFoundError:
            pass

    return JsonResponse(data={}, status=status.HTTP_200_OK)


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def upvotes_recv_api(request, format=None):
    """
    Display a list of users who liked auth user's profile.
    This is the 'upvotes inbox' page.
    """
    # pg = int(request.GET.get('page', 1))

    # get a queryset with all profiles that are "ignored" by authuser
    nopes_qs = User.objects.filter(flags_received__sender=request.user,
                                   flags_received__flag=Flag.NOPE_FLAG)

    # fetch all users that sent an upvote to authuser and did not receive
    # a downvote (hide) from authuser.
    user_list = User.objects.filter(
        flags_sent__receiver=request.user, flags_sent__flag=Flag.LIKE_FLAG) \
        .annotate(flag_created=F('flags_sent__created'))\
        .exclude(pk__in=nopes_qs).order_by('-flags_sent__created') \
        .prefetch_related('profile')[:500]

    # user_list = get_paginated_user_list(user_list, pg, request.user)
    # user_list.object_list = add_matches_to_user_list(user_list.object_list,
    #                                                  request.user)
    # Reset the "new_likes_count" value
    request.user.profile.new_likes_count = 0
    request.user.profile.save(update_fields=['new_likes_count'])

    return JsonResponse(data={
        'user_list': BasicUserSerializer(user_list, many=True).data,
    })


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def matches_api(request, format=None):
    """
    Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    # pg = int(request.GET.get('page', 1))

    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    user_list = get_matches_user_list(request.user)[:500]
    # user_list = get_paginated_user_list(user_list, pg, request.user)

    # Recount the total matches number to correct for countring errors.
    request.user.profile.matches_count = count_matches(request.user)

    # Reset the new_matches_count value
    request.user.profile.new_matches_count = 0
    request.user.profile.save(update_fields=['matches_count',
                                             'new_matches_count'])
    return JsonResponse(data={
        'user_list': BasicUserSerializer(user_list, many=True).data,
    })


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def upvotes_sent_api(request, format=None):
    """
    Display a list of users liked by auth user, i.e. sent upvotes, including
    those that are "matches" (mutual upvotes).
    """
    user_list = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.LIKE_FLAG)\
        .annotate(flag_created=F('flags_received__created'))\
        .prefetch_related('profile').order_by('-flags_received__created')[:500]

    # user_list = get_paginated_user_list(user_list, pg, request.user)
    # user_list.object_list = add_matches_to_user_list(user_list.object_list,
    #                                                  request.user)
    return JsonResponse(data={
        'user_list': BasicUserSerializer(user_list, many=True).data,
    })


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def downvotes_sent_api(request, format=None):
    """
    Display a list of users auth user noped.
    """
    pg = int(request.GET.get('page', 1))
    user_list = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.NOPE_FLAG).prefetch_related('profile')
    user_list = get_paginated_user_list(user_list, pg, request.user)

    return JsonResponse(data={
        'user_list': BasicUserSerializer(user_list, many=True).data,
    })


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def visits_api(request, format=None):
    #
    # TODO
    #
    return JsonResponse(data={
        'user_list': {},
    })


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["GET", "HEAD"])
def visitors_api(request, format=None):
    """
    Display a list of users who recently viewed auth user's profile.
    """
    # TODO Remove pagination and limit to 500 or so.
    # TODO make sure order by visit time and add visit time to sericalized data

    pg = int(request.GET.get('page', 1))

    # fetch last 1000 visitors list
    vl = request.user.was_visited.filter(
        visitor__last_login__isnull=False, visitor__is_active=True,
        hidden=False).order_by('-visitor').distinct('visitor').prefetch_related(
        'visitor').values_list('visitor__username', 'created')[:1000]

    # fetch the User qs
    user_list = User.objects.filter(username__in=[x[0] for x in vl])
    user_list = get_paginated_user_list(user_list, pg, request.user)
    user_list.object_list = add_likes_sent(user_list.object_list, request.user)
    user_list.object_list = add_likes_recv(user_list.object_list, request.user)
    user_list.object_list = add_matches_to_user_list(user_list.object_list,
                                                     request.user)
    # attach "visited" property to each user
    for u in user_list.object_list:
        try:
            v = [x[1] for x in vl if x[0] == u.username][0]
            setattr(u, 'visit_created', v)
        except IndexError:
            setattr(u, 'visit_created', None)
    user_list = sorted(user_list, key=lambda x: x.visit_created, reverse=True)

    # Reset the new_views_count value
    request.user.profile.new_views_count = 0
    request.user.profile.save(update_fields=['new_views_count'])

    return JsonResponse(data={
        'user_list': BasicUserSerializer(user_list, many=True).data,
    })


def update_search_if_changed(opts, user, session_obj=None):
    """Update all posted search uptions in authuser's Profile."""
    changed = False
    if 'order_by' in opts and session_obj is not None:
        if session_obj.get('search_results_order', None) != opts['order_by']:
            changed = True
        session_obj['search_results_order'] = opts['order_by']

    if 'f_sex' in opts:
        f_sex = force_int(opts['f_sex'])
        if user.profile.f_sex != f_sex:
            changed = True
        user.profile.f_sex = f_sex

    if 'f_distance' in opts:
        f_distance = force_int(opts['f_distance'], min=0, max=21000)
        if user.profile.f_distance != f_distance:
            changed = True
        user.profile.f_distance = f_distance

    if 'f_minage' in opts:
        f_minage = force_int(opts['f_minage'], min=18, max=99)
        if user.profile.f_minage != f_minage:
            changed = True
        user.profile.f_minage = f_minage

    if 'f_maxage' in opts:
        f_maxage = force_int(opts['f_maxage'], min=19, max=100)
        if user.profile.f_maxage != f_maxage:
            changed = True
        user.profile.f_maxage = f_maxage

    if 'f_hide_no_pic' in opts:
        f_hide_no_pic = bool(force_int(opts['f_hide_no_pic']))
        if user.profile.f_hide_no_pic != f_hide_no_pic:
            changed = True
        user.profile.f_hide_no_pic = f_hide_no_pic

    if 'f_has_verified_email' in opts:
        f_has_verified_email = bool(force_int(opts['f_has_verified_email']))
        if user.profile.f_has_verified_email != f_has_verified_email:
            changed = True
        user.profile.f_has_verified_email = f_has_verified_email

    if 'f_over_18' in opts:  # unused
        f_over_18 = bool(opts['f_over_18'])
        if user.profile.f_over_18 != f_over_18:
            changed = True
        user.profile.f_over_18 = f_over_18

    # Find active subreddits: loop through user's subs and those that are in
    # the POST are active, all others are not.
    # sr_fav = None
    if 'sr-fav' in opts:
        sr_fav = opts.get('sr-fav').split(',')
        if settings.DEBUG:
            print('# sr-fav == {}'.format(sr_fav))

        new_li = user.subs.filter(sr__display_name__in=sr_fav)
        if new_li:  # ignore empty fav list!
            cur_li = user.subs.filter(is_favorite=True)
            if new_li != cur_li:
                changed = True

            with transaction.atomic():
                user.subs.all().update(is_favorite=False)
                new_li.update(is_favorite=True)

            if settings.DEBUG:
                print('### new_li == {}'.format(new_li))
                print('### cur_li == {}'.format(cur_li))

    if settings.DEBUG:
        print('# search_results_order == {}'.format(
            session_obj['search_results_order']))
        print('# f_sex == {}'.format(user.profile.f_sex))
        print('# f_distance == {}'.format(user.profile.f_distance))

    user.profile.save(update_fields=[
        'f_sex', 'f_minage', 'f_maxage', 'f_hide_no_pic',
        'f_has_verified_email', 'f_over_18'])

    return changed


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["DELETE", "POST"])
def push_notification_api(request, format=None):
    """Create or delete a push notificaton endpoint object for auth user."""
    try:
        sub = request.body.decode('utf-8')
        _ = json.loads(sub)
    except ValueError:
        raise Http404

    if request.method == 'POST':
        PushNotificationEndpoint.objects.create(user=request.user, sub=sub)

    if request.method == 'DELETE':
        try:
            request.user.endpoints.get(sub=sub).delete()
        except PushNotificationEndpoint.DoesNotExist():
            pass

    return JsonResponse(data={})


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["DELETE", "POST"])
def flag_api(request, flag, username, format=None):
    """Let auth user set or delete a flag "flag" on user "username".
    For now options are: like, nope."""
    data = {}
    view_user = get_user_and_related_or_404(username)

    if request.method == 'POST':
        Flag.set_flag(request.user, view_user, flag)
        update_fields = ['new_likes_count']
        if flag == 'like':
            # Count the like in the view_user profile.
            view_user.profile.new_likes_count += 1
            # Check if we have a match, count it, and return {'match': 1}
            if request.user.profile.match_with(view_user):
                request.user.profile.new_matches_count += 1
                request.user.profile.save()
                view_user.profile.new_matches_count += 1
                update_fields.append('new_matches_count')
                data['is_match'] = 1
                nt = "match"
            else:
                nt = "upvote"
            simple_push_notification(request.user, view_user, nt)
            view_user.profile.save(update_fields=update_fields)

    if request.method == 'DELETE':
        # This deletes any flag, because a user can only ever set one flag on
        # another user at the same time.
        Flag.delete_flag(request.user, view_user)

    return JsonResponse(data=data)


# noinspection PyUnusedLocal
@login_required
@require_http_methods(["POST", "GET"])
def pms_list(request, username, format=None):
    """
    Send a message or retreive a partial list of messages between auth user
    and another user.

    GET api/v1/pms/<username>?after=<id>

        Return a list of x messages with an id larger than <id>, that is, more
        recently sent than the most recent message currently displayed on the
        client. If there is no message shown yet on the client and after is
        unset, then get the x most recent messages.

    POST api/v1/pms/<username> msg="Message text"&after=<id>

        Create a new message from auth user to <username>. Then return a list
        of messages with id values larger than <id>, including the just posted
        message.

    """
    view_user = get_object_or_404(User, username=username)

    if request.method == 'POST':
        body = json.loads(request.body.decode('utf-8'))
        msg = body.get('msg')
        after = body.get('after', None)

        # Store message
        kwargs = {'sender': request.user, 'receiver': view_user, 'msg': msg}
        Message.objects.create(**kwargs)

        # Send push notification to receiver
        args = [request.user, view_user, 'message', '{}'.format(msg[:60])]
        simple_push_notification(*args)

        # Respond with messages list
        return JsonResponse(data=get_msg_data(after, request.user, view_user))

    elif request.method == 'GET':
        after = request.GET.get('after', None)
        return JsonResponse(data=get_msg_data(after, request.user, view_user))


def get_msg_data(after, user1, user2):
    obj = Message.get_messages_list(after, user1, user2)
    li = MessageSerializer(obj, many=True).data
    return {'msg_list': li}
