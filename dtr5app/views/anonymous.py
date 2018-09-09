from datetime import datetime, timedelta, date

from django.conf import settings
from django.http import JsonResponse, HttpResponseNotFound, Http404, HttpResponseRedirect
from django.shortcuts import redirect, render, render_to_response, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from simple_reddit_oauth import api as reddit_api
from toolbox import force_int

from dtr5app import utils_stats
from dtr5app.models import Sr, Flag, Visit
from dtr5app.utils import add_likes_sent, add_likes_recv, add_matches_to_user_list, \
    get_paginated_user_list, get_subs_for_user
from dtr5app.utils_search import search_results_buffer, search_subreddit_users


@require_http_methods(["GET", "HEAD"])
def home_view(request):
    template_name = 'dtr5app/anonymous/home.html'

    if request.user.is_authenticated:
        return redirect(reverse('me_results_page'))

    return render(request, template_name, {
        'auth_url': reddit_api.make_authorization_url(request),
    })


@require_http_methods(["GET", "HEAD"])
def sr_view(request, sr):
    """Display a list of users who are subscribed to a subreddit.
    """
    template_name = 'dtr5app/anonymous/sr.html'
    pg = int(request.GET.get('page', 1))
    view_sr = get_object_or_404(Sr, display_name__iexact=sr)

    params = dict()
    params['order'] = request.GET.get('order', '-last_login')
    params['has_verified_email'] = bool(force_int(request.GET.get('has_verified_email', 0)))
    params['hide_no_pic'] = bool(force_int(request.GET.get('hide_no_pic', 1)))
    params['sex'] = force_int(request.GET.get('s', 0))
    params['distance'] = force_int(request.GET.get('dist', 1))

    params['minage'] = force_int(request.GET.get('minage', 18))
    if params['minage'] not in range(18, 100):
        params['minage'] = 18
    params['maxage'] = force_int(request.GET.get('maxage', 100))
    if params['maxage'] not in range(params['minage'], 101):
        params['maxage'] = 100

    if request.user.is_authenticated:
        params['user_id'] = request.user.id
        params['lat'] = request.user.profile.lat
        params['lng'] = request.user.profile.lng

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

    return render(request, template_name, {
        'view_sr': view_sr, 
        'user_list': ul, 
        'params': params,
        'user_subs_all': get_subs_for_user(request.user),
    })


def stats_view(request):
    template_name = 'dtr5app/anonymous/stats.html'

    return render(request, template_name, {
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
    })


