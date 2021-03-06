"""
All profile search-realted functions.
"""
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.datastructures import MultiValueDictKeyError

from dtr5app.models import Flag
from dtr5app.utils import normalize_sr_names
from toolbox import (to_iso8601,
                     from_iso8601,
                     get_dob_range,
                     get_latlng_bounderies, force_int, sr_str_to_list)


def search_subreddit_users(params, sr):
    """
    Fetch users subscribed to this subreddit, and return a QuerySet that can
    be paginated.

    :sr: Sr object.
    """
    return search_users_by_options_queryset(params, include_flagged=True) \
        .filter(subs__sr=sr).prefetch_related('subs').order_by('-last_login')


def get_blocked_usernames_list():
    """
    Return a list of usernames blocked by admin.

    TODO:
    """
    return []


def search_users_by_options_queryset(params, include_flagged=False):
    """
    Return a User queryset that filters by search options of the user and
    some other basic filters, like globally blocked usernames, etc. this is
    used, for example, for the Sr view user list.

    :params: a dict of search parameters.
    :user: auth user
    :include_flagged: <bool> default False. Whether to include users that were
        already flagged (like, nope, etc) by user.
    """
    # 1
    li = User.objects.all().prefetch_related('profile')

    # 2 search option: sex
    if 'sex' in params and params['sex']:
        li = li.filter(profile__sex=params['sex'])

    # 3 search option: age
    if 'minage' not in params:
        params['minage'] = 18
    if 'maxage' not in params:
        params['maxage'] = 100
    dob_earliest, dob_latest = get_dob_range(params['minage'], params['maxage'])
    li = li.filter(profile__dob__gt=dob_earliest, profile__dob__lt=dob_latest)

    # 4 search option: distance
    # Values too close are inaccurate because of location fuzzying. Also,
    # "distance" must be at least 1, so that the signup flow doesn't intercept
    # it because it has no value set! Leave this to only search distances
    # above 5 km or so, and return "worldwide" for any value below 5 km.
    if 'distance' in params and 'lat' in params and \
                    'lng' in params and params['distance'] > 5:
        lat_min, lng_min, lat_max, lng_max = get_latlng_bounderies(
            params['lat'], params['lng'], params['distance'])
        li = li.filter(profile__lat__gte=lat_min, profile__lat__lte=lat_max,
                       profile__lng__gte=lng_min, profile__lng__lte=lng_max)

    # 5 exclude auth user themself
    if 'user_id' in params:
        li = li.exclude(pk=params['user_id'])

    # 5a. exclude banned users
    li = li.exclude(is_active=False)

    # 5b. exclude users who deleted their account (i.e. last_login==None)
    li = li.exclude(last_login=None)

    # 5c. exclude users with low karma
    li = li.exclude(
        profile__link_karma__lte=settings.USER_MIN_LINK_KARMA,
        profile__comment_karma__lte=settings.USER_MIN_COMMENT_KARMA)

    # 6 are not noped by auth user ('like', 'nope', 'block')
    # if not include_flagged:
    #     li = li.exclude(flags_received__sender=user)

    # 7 are not blocked by admin via username blocklist,
    li = li.exclude(username__in=get_blocked_usernames_list())

    # 8 have at least one picture URL,
    if 'hide_no_pic' in params and params['hide_no_pic']:
        li = li.exclude(profile___pics__in=('', '[]', ))

    # 9 only users with a verified email on reddit?
    if 'has_verified_email' in params and params['has_verified_email']:
        li = li.filter(profile__has_verified_email=True)

    return li


# def get_username_list_for_search_options_only(request):
#    """
#    Return a list of usernames that are matches ONLY for auth user's
#    selected search options, and DO NOT take subreddit subscriptions into
#    consideration.
#
#    TODO: appparently not used currently.
#    """
#    BUFFER_LEN = getattr(settings, 'RESULTS_BUFFER_LEN', 500)
#    li = search_users_by_options_queryset(request.user)
#    return list(li[:BUFFER_LEN].values_list('username', flat=True))


def search_users(request, usernames_only=True):
    """
    Return a list of usernames that are matches for auth user's selected
    search options and also are subscribes to one or more of the same
    subreddits as auth user. The returned username list is ordered by the
    number of subreddits they share with auth user, with the largest number
    first.

    Search options are used only if auth user selected it, otherwise it will
    be ignored.

    The query is build as raw() SQL because there doesn't seem to be a way to
    build the subreddit subscription counting and ordering in Django.

    Since its not possible to inject the other parts into a raw() query
    (see https://code.djangoproject.com/ticket/17741), the entire query is
    build in SQL.
    """
    is_filter_block_flag_only = True
    query_params = []
    query_string = ''

    # part 1
    query_params += []
    query_string += '''
        SELECT
            au.id, au.username, ap.created, ap.accessed, ap.views_count,
            COUNT(r1.user_id) AS sr_count

        FROM dtr5app_subscribed r1

        INNER JOIN dtr5app_subscribed r2
            ON r1.sr_id = r2.sr_id AND r1.user_id <> r2.user_id

        INNER JOIN auth_user au
            ON r2.user_id = au.id

        INNER JOIN dtr5app_sr sr
            ON r1.sr_id = sr.id

        INNER JOIN dtr5app_profile ap
            ON au.id = ap.user_id

        WHERE au.is_active IS TRUE AND last_login IS NOT NULL '''

    # part 1.1
    # if the user has set a maximum size for subreddits to be considered
    # in search. this can be used to filter all the huge default subs that
    # most redditors belong to.
    #
    # REMOVED!
    #
    # if request.user.profile.f_ignore_sr_max:
    #     query_params += [request.user.profile.f_ignore_sr_max]
    #     query_string += ''' AND sr.subscribers < %s '''

    # part 1.2
    # a list of Sr.display_name values. these subreddits should NOT be
    # considered when producing matches.
    # Subreddit names should appear as case insensitive! The f_ignore_sr_li
    # list of subreddit names is supposed to be "cleaned up" already, with
    # the appropriate lettercase of a subreddit's name.
    #
    # REMOVED!
    #
    # if request.user.profile.f_ignore_sr_li:
    #     query_params += request.user.profile.f_ignore_sr_li
    #     x = ', '.join(['%s'] * len(request.user.profile.f_ignore_sr_li))
    #     query_string += ''' AND sr.id NOT IN (
    #                             SELECT id FROM dtr5app_sr sr2
    #                             WHERE sr2.display_name IN (''' + x + ' )) '

    # part 1.3
    # Search only those subs that auth user marked as their favorites. By
    # default, all subreddits a user is subbed to are their favorites, unless
    # they have manually de-selected some in the search settings.
    query_params += []
    query_string += ''' AND r1.is_favorite '''

    # part 1.9
    # Set r1 to be the auth user, and r2 to be the users we are searching for,
    # then do a sub-query to join them with their profiles, so we can search
    # the profile for auth user's search settings.
    query_params += [request.user.id]
    query_string += ''' AND r1.user_id = %s AND au.id IN (
                            SELECT id FROM auth_user u
                            INNER JOIN dtr5app_profile p
                                ON u.id = p.user_id
                            WHERE 1=1 '''

    # part 2: sex --> TODO: search by gender!
    # li = li.filter(profile__sex=request.user.profile.f_sex)
    if request.user.profile.f_sex > 0:
        query_params += [request.user.profile.f_sex]
        query_string += ''' AND p.sex = %s '''

    # part 3: date of birth
    dob_earliest, dob_latest = get_dob_range(request.user.profile.f_minage,
                                             request.user.profile.f_maxage)
    query_params += [dob_earliest, dob_latest]
    query_string += ''' AND p.dob >= %s AND p.dob <= %s '''

    # part 4: lat/lng
    # li = li.filter(profile__lat__gte=lat_min, profile__lat__lte=lat_max,
    #                profile__lng__gte=lng_min, profile__lng__lte=lng_max)
    #
    # Values too close are inaccurate because of location fuzzying. Also,
    # f_distance must be at least 1, so that the signup flow doesn't intercept
    # it because it has no value set! Leave this to only search distances
    # above 5 km or so, and return "worldwide" for any value below 5 km.
    #
    if request.user.profile.f_distance > 5:
        lat_min, lng_min, lat_max, lng_max = get_latlng_bounderies(
            request.user.profile.lat,
            request.user.profile.lng,
            request.user.profile.f_distance)
        query_params += [lat_max, lng_min, lat_min, lng_max]
        query_string += ''' AND p.lat <= %s AND p.lng >= %s
                            AND p.lat >= %s AND p.lng <= %s '''

    # part 5: exclude auth user themself
    # li = li.exclude(pk=request.user.pk)
    query_params += [request.user.id]
    query_string += ''' AND NOT (u.id = %s) '''

    # part 6: exclude users who already have a like/nope flag from auth user
    # li = li.exclude(flags_received__sender=request.user)
    if is_filter_block_flag_only:
        # exclude only users who have a BLOCK_FLAG ("hide") from auth user
        query_params += [Flag.BLOCK_FLAG, request.user.id]
        query_string += ''' AND NOT (u.id IN (SELECT U1.receiver_id AS Col1
                            FROM dtr5app_flag U1
                            WHERE U1.flag = %s AND U1.sender_id = %s)) '''
    else:
        # Exclude all users flagged by auth user: LIKE_FLAG, BLOCK_FLAG, etc.
        query_params += [request.user.id]
        query_string += ''' AND NOT (u.id IN (SELECT U1.receiver_id AS Col1
                            FROM dtr5app_flag U1 WHERE U1.sender_id = %s)) '''

    # part 7: exclude globally blocked usernames
    # li = li.exclude(username__in=get_blocked_usernames_list())
    # --> TODO: currently empty.
    pass

    # part 8: have at least one picture URL in the JSON string
    # li = li.exclude(profile___pics='[]')
    #
    # TODO: for now, allow no-picture profiles, to make testing easier
    #
    # Note: there was an error causing an empty pic list to be written as [] to
    #       the field.
    if request.user.profile.f_hide_no_pic:
        query_params += []
        query_string += ''' AND p._pics NOT IN ('', '[]') '''

    # part 9: only users with a verified email on reddit
    # li = li.filter(profile__has_verified_email=True)
    if request.user.profile.f_has_verified_email:
        query_params += []
        query_string += ''' AND p.has_verified_email '''

    # finish up: fetch 1000 matches with most subs in common
    query_params += [getattr(settings, 'RESULTS_BUFFER_LEN', 1000)]
    query_string += ''' ) GROUP BY r1.user_id, au.id, ap.user_id
                          ORDER BY sr_count DESC LIMIT %s '''
    users = User.objects.raw(query_string, query_params)

    # re-order the results: re-order the 1000 matches by the value stored in the
    # user's session, so they can see seemingly different kinds of lists.
    order_by = request.session.get('search_results_order', '')

    if order_by == '-accessed':  # most recently accessed first
        users = sorted(users, key=lambda u: u.accessed, reverse=True)
    elif order_by == 'accessed':  # most recently accessed last
        users = sorted(users, key=lambda u: u.accessed, reverse=False)
    elif order_by == 'date_joined':  # oldest redddate account
        users = sorted(users, key=lambda u: u.date_joined, reverse=True)
    elif order_by == '-date_joined':  # most recent redddate acccount
        users = sorted(users, key=lambda u: u.date_joined, reverse=True)
    # Not posstible because of the "created" bug when it fetched a unixtime of
    # "0" from reddit. There are still many accounts that have a "created" date
    # set to "1970-01-01T00:00:00".
    #
    # elif order_by == 'reddit_joined':  # oldest REDDIT account
    #     users = sorted(users, key=lambda u: u.created, reverse=False)
    # elif order_by == '-reddit_joined':  # most recent REDDIT account
    #     users = sorted(users, key=lambda u: u.created, reverse=True)
    elif order_by == '-views_count':  # most views first
        users = sorted(users, key=lambda u: u.views_count, reverse=True)
    elif order_by == 'views_count':  # most views last
        users = sorted(users, key=lambda u: u.views_count, reverse=False)
    else:  # -sr_count (default): most subs in common first
        users = sorted(users, key=lambda u: u.sr_count, reverse=True)

    # default return a list of only usernames
    if usernames_only:
        return [x.username for x in users]
    else:
        return users


def search_results_buffer(request, force=False):
    """
    Check if there are search results in session cache. If there are
    not, or 'force' is True, run a search and load the usernames into
    the buffer.
    """
    bt = request.session.get('search_results_buffer_time', None)
    mt = getattr(settings, 'RESULTS_BUFFER_TIMEOUT', 5)

    if not bt or from_iso8601(bt) + timedelta(minutes=mt) < from_iso8601():
        if settings.DEBUG:
            print('search_results_buffer() --> Cache timeout, new search!')
        force = True  # if buffer is old, force refresh

    if request.session.get('search_results_buffer', None) is None:
        if settings.DEBUG:
            print('search_results_buffer() --> No buffer, fill first time!')
        force = True  # no buffer ever set, then do a search

    if force:
        if settings.DEBUG:
            print('search_results_buffer() --> "force" is true, do search!')

        request.session['search_results_buffer'] = search_users(request)
        request.session['search_results_buffer_time'] = to_iso8601()
        request.session.modified = True


def update_search_settings(request):
    """Update all posted search uptions in authuser's Profile."""
    p = request.user.profile

    if 'order_by' in request.POST:
        request.session['search_results_order'] = request.POST['order_by']

    if 'f_sex' in request.POST:
        p.f_sex = force_int(request.POST['f_sex'])

    if 'f_distance' in request.POST:
        p.f_distance = force_int(request.POST['f_distance'], min=0, max=21000)

    if 'f_minage' in request.POST:
        p.f_minage = force_int(request.POST['f_minage'], min=18, max=99)

    if 'f_maxage' in request.POST:
        p.f_maxage = force_int(request.POST['f_maxage'], min=19, max=100)

    if 'f_hide_no_pic' in request.POST:
        j = force_int(request.POST['f_hide_no_pic'])
        p.f_hide_no_pic = bool(j)

    if 'f_has_verified_email' in request.POST:
        j = force_int(request.POST['f_has_verified_email'])
        p.f_has_verified_email = bool(j)

    # TODO: needs Profile model update!
    # if 'f_is_stable' in request.POST:
    #     j = force_int(request.POST['f_is_stable'])
    #     p.f_is_stable = bool(j)

    if 'f_over_18' in request.POST:  # unused
        p.f_over_18 = bool(request.POST['f_over_18'])

    # List of subreddit names. This needs to be cleaned for appropriate
    # letter case, so its useful in raw SQL search. Since Django has no
    # case insensivity support :( we look up the correctly cased subreddit
    # names here once, and store those as the user's search settings.
    # --> REMOVE from search, use "fav subreddits" list instead.
    if 'f_ignore_sr_li' in request.POST:
        try:
            li = sr_str_to_list(request.POST['f_ignore_sr_li'])
            p.f_ignore_sr_li = normalize_sr_names(li)
        except MultiValueDictKeyError:
            pass  # don't change the search value if not POSTed.

    # --> REMOVE from search, use "fav subreddits" list instead.
    if 'f_ignore_sr_max' in request.POST:
        try:
            p.f_ignore_sr_max = force_int(request.POST['f_ignore_sr_max'],
                                          min=100, max=123456789)
        except MultiValueDictKeyError:
            pass  # don't change the search vaue if not POSTed.

    # Currently unused.
    if 'f_exclude_sr_li' in request.POST:
        try:
            li = sr_str_to_list(request.POST['f_exclude_sr_li'])
            p.f_exclude_sr_li = normalize_sr_names(li)
        except MultiValueDictKeyError:
            pass  # don't change the search value if not POSTed.

    # Find active subreddits: loop through user's subs and those that are in
    # the POST are active, all others are not.
    if 'sr-fav' in request.POST:
        posted = request.POST.getlist('sr-fav')
        li = request.user.subs.filter(sr__display_name__in=posted)
        if li:  # ignore empty fav list!
            with transaction.atomic():
                request.user.subs.all().update(is_favorite=False)
                li.update(is_favorite=True)
        else:
            messages.warning(request, 'no subreddits selected for search!')

    request.user.profile = p
    request.user.profile.save()
    return request
