from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, Http404, HttpResponseNotFound, \
    HttpResponse
from django.views.decorators.http import require_http_methods
from os.path import join

from dtr5app.models import Visit
from dtr5app.templatetags.dtr5tags import prefdist
from dtr5app.utils import add_likes_sent, add_likes_recv, \
    add_matches_to_user_list, add_auth_user_latlng, prepare_paginated_user_list, \
    get_user_list_from_username_list, get_user_and_related_or_404, \
    get_user_list_after, get_prevnext_user
from dtr5app.utils_search import search_results_buffer


def serialize_object_property(obj, prop):
    """
    For an object with properties like `my_obj.some.prop.here` and props being
    'some.prop.here', it returns ret['some']['prop']['here']

    Args:
        obj: Python object
        prop: Objects property name in dotted notation.

    Returns:
        A dictionary of dictionaries.
    """
    if prop:
        if '.' in prop:
            this_prop, child_prop = prop.split('.', 1)
            this_obj = getattr(obj, this_prop)
            if isinstance(this_obj, object):
                return {this_prop: serialize_object_property(this_obj, child_prop)}
            else:
                return this_obj

        return {prop: getattr(obj, prop, None)}


def serialize_object(obj, props):
    return [serialize_object_property(obj, prop) for prop in props]


def serialize_object_list(obj_list, props):
    """
    Serialize a list of objects into a list of dictionaries.
    """
    return [serialize_object(obj, props) for obj in obj_list]


@require_http_methods(["GET", "HEAD"])
def app_index_view(request):
    """
    For development only. Serve static files from /app/ route. For files
    that don't exist, always serve app/index.html
    """
    f = join(settings.BASE_DIR, '../../reddmeet-material/app/index.html')
    with open(f, 'r') as fh:
        return HttpResponse(fh.read())


@require_http_methods(["GET"])
def filter_members(request):
    """
    GETs a list of usernames.

    Returns a list of user simple user objects.
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

    return JsonResponse({'user_list': response_data})


@login_required
def results(request):
    """
    Show a page of search results from auth user's search buffer.

    """
    pg = int(request.GET.get('page', 1))

    search_results_buffer(request)

    ul = request.session['search_results_buffer']
    ul = prepare_paginated_user_list(ul, pg)
    ul.object_list = get_user_list_from_username_list(ul.object_list)
    ul.object_list = add_auth_user_latlng(request.user, ul.object_list)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)

    print(ul[0].profile.age)
    return JsonResponse({
        'user_list': serialize_object_list(ul, [
            'username', 'profile.sex', 'profile.age',
        ])
    })


@login_required
def profile(request, username):
    """
    Show a page of search results from auth user's search buffer.

    """
    """
    Display the complete profile of one user, together with "like" and "nope"
    buttons, unless auth user is viewing their own profile.
    """
    view_user = get_user_and_related_or_404(username, 'profile', 'subs')

    if not view_user.is_active:
        return HttpResponseNotFound('user was banned')
    if not view_user.last_login:
        raise Http404  # user deleted their account

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

    # TODO: Fix that we sometimes call a method on view_user's profile with
    # TODO: request.user as arg, and sometimes we call a method on req.user's
    # TODO: profile with view_user as arg. :/ Should just set once req.user
    # TODO: as "partner" on the view_user profile and then have all those
    # TODO: methods re-use that setting.
    return JsonResponse({
        'view_user': {
            'username': view_user.username,
        },
        # 'show_created': show_created,
        # 'user_list': user_list,
        # 'common_subs': view_user.profile.get_common_subs(request.user),
        # 'not_common_subs':view_user.profile.get_not_common_subs(request.user),
        # 'is_match': request.user.profile.match_with(view_user),
        # 'is_like': request.user.profile.does_like(view_user),
        # 'is_nope': request.user.profile.does_nope(view_user),
        # 'prev_user': prev_user,
        # 'next_user': next_user,
    })


def authuser_subreddit_list(request):
    """
    Return the list of subreddits of authuser, with `is_favorite` set.
    """
    sr_list = []
    for row in request.user.subs.all().prefetch_related('sr'):
        # We need the name of the SR and the status "is_favorite" as "1" or "0".
        fav = 1 if row.is_favorite else 0
        sr_list.append({'name': row.sr.display_name, 'fav': fav})

    return JsonResponse({'sr_list': sr_list})
