import pytz

from datetime import datetime, timedelta, date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import JsonResponse, Http404, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import redirect, render, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from toolbox import force_int

from dtr5app.models import Sr, Flag, Visit
from dtr5app.utils import (
    add_auth_user_latlng, 
    count_matches, 
    get_matches_user_list,
    get_prevnext_user, 
    get_user_and_related_or_404, 
    get_paginated_user_list,
    prepare_paginated_user_list, 
    add_matches_to_user_list, 
    get_user_list_from_username_list,
    get_user_list_after, 
    add_likes_sent, 
    add_likes_recv, 
    get_subs_for_user,
)
from dtr5app.utils_search import search_results_buffer, search_subreddit_users


@login_required
def results_view(request):
    """Show a page of search results from auth user's search buffer.
    """
    template_name = 'dtr5app/authenticated/results.html'
    pg = int(request.GET.get('page', 1))
    order_by = request.session.get('search_results_order', '')

    search_results_buffer(request)

    ul = prepare_paginated_user_list(request.session['search_results_buffer'], pg)
    ul.object_list = get_user_list_from_username_list(ul.object_list)
    ul.object_list = add_auth_user_latlng(request.user, ul.object_list)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)

    sr_names = []
    for row in request.user.subs.all().prefetch_related('sr'):
        # We need the name of the SR and the status "is_favorite" as "1" or "0".
        fav = 1 if row.is_favorite else 0
        sr_names.append({'name': row.sr.display_name, 'fav': fav})

    return render(request, template_name, {
        'user_list': ul,
        'order_by': order_by,
        'sr_names': sr_names,
    })


@login_required
def profile_view(request, username):
    """Display the complete profile of one user, together with "like" 
    and "nope" buttons, unless auth user is viewing their own profile.
    """
    template_name = 'dtr5app/authenticated/profile.html'
    view_user = get_user_and_related_or_404(username, 'profile', 'subs')

    if not view_user.is_active:
        return HttpResponseNotFound('user was banned')
    if not view_user.last_login:
        raise Http404  # user deleted their account

    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat, request.user.profile.lng)

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
            view_user.profile.save(update_fields=['views_count', 'new_views_count'])
        request.session['last_viewed_users'].append(view_user.pk)

        # remember the view for visitor history
        Visit.add_visitor_host(request.user, view_user)

    # there was an error with the "created" timestamp handling, so some were
    # set to "0", i.e. Epoch time 1970-01-01. Filter those out.
    show_created = (view_user.profile.created and view_user.profile.created > date(1970, 1, 1))

    # TODO: Fix that we sometimes call a method on view_user's profile with
    # TODO: request.user as arg, and sometimes we call a method on req.user's
    # TODO: profile with view_user as arg. :/ Should just set once req.user
    # TODO: as "partner" on the view_user profile and then have all those
    # TODO: methods re-use that setting.
    return render(request, template_name, {
        'show_created': show_created,
        'view_user': view_user,
        'user_list': user_list,
        'common_subs': view_user.profile.get_common_subs(request.user),
        'not_common_subs': view_user.profile.get_not_common_subs(request.user),
        'is_match': request.user.profile.match_with(view_user),
        'is_like': request.user.profile.does_like(view_user),
        'is_nope': request.user.profile.does_nope(view_user),
        'prev_user': prev_user,
        'next_user': next_user,
    })


@login_required
@require_http_methods(["GET", "HEAD"])
def nope_view(request):
    """Display a list of users auth user noped.
    """
    template_name = 'dtr5app/authenticated/nopes.html'
    pg = int(request.GET.get('page', 1))
    ul = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.NOPE_FLAG
    ).prefetch_related('profile')

    return render(request, template_name, {
        'user_list': get_paginated_user_list(ul, pg, request.user),
    })


@login_required
@require_http_methods(["GET", "HEAD"])
def viewed_me_view(request):
    """Display a list of users who recently viewed auth user's profile.
    """
    template_name = 'dtr5app/authenticated/viewed_me.html'
    pg = int(request.GET.get('page', 1))

    # fetch last 1000 visitors list
    vl = request.user.was_visited.filter(
        visitor__last_login__isnull=False, visitor__is_active=True,
        hidden=False).order_by('-visitor').distinct('visitor').prefetch_related(
        'visitor').values_list('visitor__username', 'created')[:1000]

    # fetch the User qs
    ul = User.objects.filter(username__in=[x[0] for x in vl])
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    # attach "visited" property to each user
    for u in ul.object_list:
        try:
            v = [x[1] for x in vl if x[0] == u.username][0]
            setattr(u, 'visit_created', v)
        except IndexError:
            setattr(u, 'visit_created', None)

    # Reset the new_views_count value
    request.user.profile.new_views_count = 0
    request.user.profile.save(update_fields=['new_views_count'])

    return render(request, template_name, {
        'user_list': sorted(ul, key=lambda x: x.visit_created, reverse=True),
    })


@login_required
@require_http_methods(["GET", "HEAD"])
def likes_sent_view(request):
    """Display a list of users liked by auth user, i.e. sent upvotes,
    including those that are "matches" (mutual upvotes).
    """
    template_name = 'dtr5app/authenticated/likes_sent.html'
    pg = int(request.GET.get('page', 1))
    ul = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.LIKE_FLAG,
    ).prefetch_related('profile')

    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    return render(request, template_name, {'user_list': ul})


@login_required
@require_http_methods(["GET", "HEAD"])
def likes_recv_view(request):
    """Display a list of users who liked auth user's profile.
    This is the 'upvotes inbox' page.
    """
    template_name = 'dtr5app/authenticated/likes_recv.html'
    pg = int(request.GET.get('page', 1))

    # get a queryset with all profiles that are "ignored" by authuser
    nopes_qs = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.NOPE_FLAG,
    )

    # fetch all users that sent an upvote to authuser and did not receive
    # a downvote (hide) from authuser.
    ul = User.objects\
        .filter(flags_sent__receiver=request.user, flags_sent__flag=Flag.LIKE_FLAG)\
        .exclude(pk__in=nopes_qs)\
        .order_by('-flags_sent__created')\
        .prefetch_related('profile')

    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    # Reset the "new_likes_count" value
    request.user.profile.new_likes_count = 0
    request.user.profile.save(update_fields=['new_likes_count'])

    return render(request, template_name, {'user_list': ul})


@login_required
@require_http_methods(["GET", "HEAD"])
def matches_view(request):
    """Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    template_name = 'dtr5app/authenticated/matches.html'
    pg = int(request.GET.get('page', 1))

    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    ul = get_matches_user_list(request.user)
    ul = get_paginated_user_list(ul, pg, request.user)

    # Recount the total matches number to correct for countring errors.
    request.user.profile.matches_count = count_matches(request.user)

    # Reset the new_matches_count value
    request.user.profile.new_matches_count = 0
    request.user.profile.save(update_fields=['matches_count',
                                             'new_matches_count'])
    return render(request, template_name, {'user_list': ul})


@login_required
@require_http_methods(["GET"])
def usermap_view(request):
    template_name = 'dtr5app/authenticated/usermap.html'

    if request.is_ajax():
        west = request.GET.get('west', None)
        south = request.GET.get('south', None)
        east = request.GET.get('east', None)
        north = request.GET.get('north', None)
        t = force_int(request.GET.get('t', 0))

        if settings.DEBUG:
            print(west, north, east, south, t)

        users = User.objects.exclude(
            profile__lat__gte=-0.1,
            profile__lng__gte=-0.1,
            profile__lat__lte=1.1,
            profile__lng__lte=1.1,
        ).filter(
            profile__lat__gte=south,
            profile__lng__gte=west,
            profile__lat__lte=north,
            profile__lng__lte=east,
            is_active=True,
            last_login__isnull=False,
        )

        if t > 0:
            tmin = datetime.now().replace(tzinfo=pytz.utc) - timedelta(minutes=t)
            users = users.filter(profile__accessed__gte=tmin)

        return JsonResponse({'users': [
            [u.username, u.profile.lat, u.profile.lng]
            for u in users.prefetch_related('profile')[:250]
        ]})

    return render(request, template_name, {})
