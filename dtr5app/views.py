import pytz
from datetime import datetime, timedelta, date
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import JsonResponse, HttpResponse, \
                        HttpResponseNotFound, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from simple_reddit_oauth import api
from toolbox import force_int

from . import utils_stats
from .models import Sr, Flag, Report, Visit
from .utils import add_auth_user_latlng, count_matches, get_matches_user_list, \
                   get_prevnext_user, get_user_and_related_or_404, \
                   get_user_list_after, \
                   get_paginated_user_list, prepare_paginated_user_list, \
                   add_matches_to_user_list, get_user_list_from_username_list, \
    add_likes_sent, add_likes_recv
from .utils_search import search_results_buffer, search_subreddit_users, \
                          update_search_settings


@require_http_methods(["GET", "HEAD"])
def home_view(request, template_name='dtr5app/home_anon.html'):
    if request.user.is_authenticated():
        return redirect(reverse('me_results_page'))

    ctx = {'auth_url': api.make_authorization_url(request)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def me_results_view(request, template_name='dtr5app/results.html'):
    """
    Show a page of search results from auth user's search buffer.

    """
    pg = int(request.GET.get('page', 1))
    search_results_buffer(request)
    li = request.session['search_results_buffer']
    li = prepare_paginated_user_list(li, pg)
    li.object_list = get_user_list_from_username_list(li.object_list)
    li.object_list = add_auth_user_latlng(request.user, li.object_list)

    ctx = {'user_list': li,
           'order_by': request.session.get('search_results_order', '')}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def profile_view(request, username, template_name='dtr5app/profile.html'):
    """
    Display the complete profile of one user, together with "like" and "nope"
    buttons, unless auth user is viewing their own profile.
    """
    view_user = get_user_and_related_or_404(username, 'profile', 'subs')

    if not view_user.is_active:
        # user was banned
        return HttpResponseNotFound('user was banned')
    if not view_user.last_login:
        # user deleted their account
        raise Http404

    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat,
                                        request.user.profile.lng)

    # Make sure there is a list of 10 pic objects, empty or not.
    setattr(view_user, 'pics_list', view_user.profile.pics[:10])
    view_user.pics_list += [None] * (10 - len(view_user.pics_list))

    # Find the SRs that auth user and view user have in common, EXCLUDING all
    # SRs that are filtered by auth users "ignore_sr_li" and "ignore_sr_max"
    # search settings.
    view_user.profile.set_common_subs(request.user.subs.all(),
                                      request.user.profile.f_ignore_sr_li,
                                      request.user.profile.f_ignore_sr_max)

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

    ctx = {'show_created': show_created,
           'view_user': view_user,
           'is_match': request.user.profile.match_with(view_user),
           'is_like': request.user.profile.does_like(view_user),
           'is_nope': request.user.profile.does_nope(view_user),
           'lookingfor_choices': settings.LOOKINGFOR,
           'user_list': user_list,
           'prev_user': prev_user,
           'next_user': next_user}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def sr_view(request, sr, template_name='dtr5app/sr.html'):
    """
    Display a list of users who are subscribed to a subreddit.
    """
    pg = int(request.GET.get('page', 1))
    order_by = request.POST.get('order_by', '-last_login')
    view_sr = get_object_or_404(Sr, display_name__iexact=sr)

    # TODO: remove this and display User subset by GET parameters, to not mis
    # TODO: it up with the regular search settings in /results/ here.
    update_search_settings(request)

    ul = search_subreddit_users(request.user, view_sr)
    if order_by == '-accessed':  # most recently accessed first
        ul = ul.order_by('-profile__accessed')
    elif order_by == '-date_joined':  # most recent redddate acccount
        ul = ul.order_by('-date_joined')
    elif order_by == '-views_count':  # most views first
        ul = ul.order_by('-profile__views_count')

    # Paginate and add "is_like_recv" and "is_like"sent"
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_likes_sent(ul.object_list, request.user)
    ul.object_list = add_likes_recv(ul.object_list, request.user)

    ctx = {'view_sr': view_sr,
           'user_list': ul,
           'user_subs_all': request.user.subs.all().prefetch_related('sr'),
           'order_by': request.session.get('search_results_order', '')}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_nope_view(request):
    """
    Display a list of users auth user noped.
    """
    template_name = 'dtr5app/nopes.html'
    pg = int(request.GET.get('page', 1))
    ul = User.objects.filter(flags_received__sender=request.user,
                             flags_received__flag=Flag.NOPE_FLAG
                             ).prefetch_related('profile')
    ctx = {'user_list': get_paginated_user_list(ul, pg, request.user)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_viewed_me_view(request):
    """
    Display a list of users who recently viewed auth user's profile.
    """
    template_name = 'dtr5app/viewed_me.html'
    pg = int(request.GET.get('page', 1))

    # fetch last 1000 visitors list
    vl = request.user.was_visited.filter(
        hidden=False, visitor__last_login__isnull=False,
        visitor__is_active=True).order_by('-visitor').distinct('visitor')\
        .prefetch_related('visitor')\
        .values_list('visitor__username', 'created')[:1000]

    # fetch the User qs
    ul = User.objects.filter(username__in=[x[0] for x in vl])
    ul = get_paginated_user_list(ul, pg, request.user)

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

    ctx = {'user_list': sorted(ul, key=lambda x: x.visit_created,
                               reverse=True)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_like_view(request):
    """
    Display a list of users liked by auth user, i.e. sent upvotes, including
    those that are "matches" (mutual upvotes).
    """
    template_name = 'dtr5app/likes_sent.html'
    pg = int(request.GET.get('page', 1))
    ul = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.LIKE_FLAG).prefetch_related('profile')
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    ctx = {'user_list': ul}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_recv_like_view(request):
    """
    Display a list of users who liked auth user's profile.
    This is the 'upvotes inbox' page.
    """
    template_name = 'dtr5app/likes_recv.html'
    pg = int(request.GET.get('page', 1))

    # get a queryset with all profiles that are "ignored" by authuser
    nopes_qs = User.objects.filter(flags_received__sender=request.user,
                                   flags_received__flag=Flag.NOPE_FLAG)
    # fetch all users that sent an upvote to authuser and did not receive
    # a downvote (hide) from authuser.
    ul = User.objects.filter(flags_sent__receiver=request.user,
                             flags_sent__flag=Flag.LIKE_FLAG)\
                     .exclude(pk__in=nopes_qs)\
                     .prefetch_related('profile')
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    # Reset the new_likes_count value
    request.user.profile.new_likes_count = 0
    request.user.profile.save(update_fields=['new_likes_count'])

    ctx = {'user_list': ul}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def matches_view(request):
    """
    Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    template_name = 'dtr5app/matches.html'
    # pg = int(request.GET.get('page', 1))
    user_list = get_matches_user_list(request.user)
    user_list = add_auth_user_latlng(request.user, user_list)

    #
    # TODO: pagination!!!
    #

    # Recount the total matches number to correct for countring errors.
    request.user.profile.matches_count = count_matches(request.user)
    # Reset the new_matches_count value
    request.user.profile.new_matches_count = 0
    request.user.profile.save(update_fields=['matches_count',
                                             'new_matches_count'])
    ctx = {'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@staff_member_required
@require_http_methods(["GET", "POST"])
def mod_report_view(request, pk=None):
    """
    For staff users to review reported profiles. If a pk is given on a POST,
    set that report to "resolved".
    """
    show = request.POST.get('show', None) or request.GET.get('show', 'open')

    if request.method in ['POST']:
        # toggle the resove state of the report.
        report = get_object_or_404(Report, pk=pk)
        if report.resolved:
            report.resolved = None
        else:
            report.resolved = datetime.now().replace(tzinfo=pytz.utc)
        report.save()
        # then show the same list, either "open" or "resolved"
        return redirect(reverse('mod_report_page') + '?show=' + show)

    template_name = 'dtr5app/reports.html'
    li = Report.objects.prefetch_related('sender', 'receiver')
    if show == 'resolved':
        # show list of old resolved reports
        li = li.filter(resolved__isnull=False).order_by('-resolved')
    else:
        # or a list of fresh open reports
        li = li.filter(resolved__isnull=True).order_by('-created')

    paginator = Paginator(li, per_page=100)
    try:
        reports = paginator.page(int(request.GET.get('page', 1)))
    except EmptyPage:  # out of range
        return HttpResponseNotFound()
    except ValueError:  # not a number
        return HttpResponseNotFound()

    ctx = {'reports': reports, 'show': show}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@staff_member_required
def mod_deluser_view(request, pk):
    """for moderators to delete a user profile and ban the user"""
    view_user = get_object_or_404(User, pk=pk)

    if request.method in ["POST"]:
        view_user.profile.reset_all_and_save()
        view_user.subs.all().delete()
        view_user.flags_sent.all().delete()
        view_user.flags_received.all().delete()
        # if user's last_login is None means they have not activated their
        # account or have deleted it. either way, treat it as if it doesn't
        # exist. ~~view_user.last_login = None~~
        # view_user.date_joined = None  # can't be None, so leave it
        #
        # Setting an account to "is_active = False" will prevent the user from
        # using the same reddit account to sign up again. If "is_active = True"
        # then the user will be able to sign up again, using the same reddit
        # account.
        view_user.is_active = False
        view_user.save()
        kwargs = {'username': view_user.username}
        return redirect(reverse('profile_page', kwargs=kwargs))

    template_name = 'dtr5app/mod_del_profile.html'
    ctx = {'view_user': view_user}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


def stats(request, template_name='dtr5app/stats.html'):

    ctx = {
        'users_by_sex': utils_stats.get_users_by_sex(),
        'likes_count': utils_stats.get_likes_count(),
        'nopes_count': utils_stats.get_nopes_count(),
        'matches_count': utils_stats.get_matches_count(),

        # active users in the past 1, 5, and 15 minutes
        'users_active_1m': utils_stats.get_active_users(1),
        'users_active_5m': utils_stats.get_active_users(5),
        'users_active_15m': utils_stats.get_active_users(15),
        'users_active_1h': utils_stats.get_active_users(60),  # past hour
        'users_active_24h': utils_stats.get_active_users(24*60),  # past 24h
        'users_active_7d': utils_stats.get_active_users(7*24*60),  # past 7d
        'users_active_30d': utils_stats.get_active_users(30*24*60),  # past 30d
        'users_active_90d': utils_stats.get_active_users(90*24*60),  # past 90d
        'users_active_1y': utils_stats.get_active_users(356*24*60),  # past 1y

        'signups_per_day': utils_stats.get_signups_per_day_for_range(
            (date.today() - timedelta(days=30)), date.today())
    }

    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET"])
def usermap(request, template_name='dtr5app/usermap.html'):
    if request.is_ajax():
        west = request.GET.get('west', None)
        south = request.GET.get('south', None)
        east = request.GET.get('east', None)
        north = request.GET.get('north', None)
        t = force_int(request.GET.get('t', 0))

        if settings.DEBUG:
            print(west, north, east, south, t)

        users = User.objects.exclude(
            profile__lat__gte=-0.1, profile__lng__gte=-0.1,
            profile__lat__lte=1.1, profile__lng__lte=1.1
            ).filter(
            profile__lat__gte=south, profile__lng__gte=west,
            profile__lat__lte=north, profile__lng__lte=east,
            is_active=True, last_login__isnull=False)

        if t > 0:
            tmin = datetime.now().replace(tzinfo=pytz.utc)-timedelta(minutes=t)
            users = users.filter(profile__accessed__gte=tmin)

        users = [[u.username, u.profile.lat, u.profile.lng]
                 for u in users.prefetch_related('profile')[:250]]
        return JsonResponse({'users': users})

    ctx = {}
    kwargs = {'context_instance': RequestContext(request)}
    return render_to_response(template_name, ctx, **kwargs)
