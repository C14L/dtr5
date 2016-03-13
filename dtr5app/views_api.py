from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from dtr5app.models import Visit
from dtr5app.serializers import UserSerializer, SubscribedSerializer
from dtr5app.templatetags.dtr5tags import prefdist
from dtr5app.utils import add_likes_sent, add_likes_recv, \
    add_matches_to_user_list, add_auth_user_latlng, \
    get_user_and_related_or_404, get_user_list_from_username_list, \
    get_user_list_after, get_prevnext_user, prepare_paginated_user_list
from dtr5app.utils_search import search_results_buffer


@require_http_methods(["GET"])
def filter_members_view(request):
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


@login_required
@api_view(['GET', ])
def results_list(request, format=None):
    """
    Show a page of search results from auth user's search buffer.
    """
    pg = int(request.GET.get('page', 1))
    order_by = request.session.get('search_results_order', '')

    search_results_buffer(request)
    ul = request.session['search_results_buffer']
    ul = prepare_paginated_user_list(ul, pg)

    ul.object_list = get_user_list_from_username_list(ul.object_list)
    ul.object_list = add_auth_user_latlng(request.user, ul.object_list)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)

    sr_names = []
    for row in request.user.subs.all().prefetch_related('sr'):
        # We need the name of the SR and the status "is_favorite" as "1" or "0".
        fav = 1 if row.is_favorite else 0
        sr_names.append({'name': row.sr.display_name, 'fav': fav})

    return Response(data={
        'user_list': UserSerializer(ul.object_list, many=True).data,
        'order_by': order_by, 'sr_names': sr_names, })


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

    return Response(data={
        'show_created': show_created,
        'view_user': UserSerializer(view_user).data,
        'prev_user': UserSerializer(prev_user).data,
        'next_user': UserSerializer(next_user).data,
        'user_list': UserSerializer(user_list, many=True).data,

        'common_subs': SubscribedSerializer(
            view_user.profile.get_common_subs(request.user), many=True).data,
        'not_common_subs': SubscribedSerializer(
            view_user.profile.get_not_common_subs(request.user), many=True).data,

        'is_match': request.user.profile.match_with(view_user),
        'is_like': request.user.profile.does_like(view_user),
        'is_nope': request.user.profile.does_nope(view_user), })

