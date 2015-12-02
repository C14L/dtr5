"""
All profile search-realted functions.
"""
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from toolbox import (to_iso8601,
                     from_iso8601,
                     get_dob_range,
                     get_latlng_bounderies)


def search_subreddit_users(user, sr):
    """
    fetch users subscribed to this subreddit return a queryset that can
    be paginated.

    :sr: Sr instance.
    """
    return search_users_by_options_queryset(user, include_flagged=True)\
        .filter(subs__sr=sr).prefetch_related('profile', 'subs')\
        .order_by('last_login')


def get_blocked_usernames_list():
    """
    Return a list of usernames blocked by admin.

    TODO:
    """
    return []


def search_users_by_options_queryset(user, include_flagged=False):
    """
    return a User queryset that filters by search options of the user and
    some other basic filters, like globally blocked usernames, etc. this is
    used, for example, for the Sr view user list.

    :user: <User instance> who's search option settings to use. Most likely,
        this is the request.user instance.

    :include_flagged: <bool> default False. Whether to include users that were
        already flagged (like, nope, etc) by user.
    """
    # 1
    li = User.objects.all()

    # 2 search option: sex
    if user.profile.f_sex > 0:
        li = li.filter(profile__sex=user.profile.f_sex)

    # 3 search option: age
    dob_earliest, dob_latest = get_dob_range(user.profile.f_minage,
                                             user.profile.f_maxage)
    li = li.filter(profile__dob__gt=dob_earliest, profile__dob__lt=dob_latest)

    # 4 search option: distance
    #
    # Values too close are inaccurate because of location fuzzying. Also,
    # f_distance must be at least 1, so that the signup flow doesn't intercept
    # it because it has no value set! Leave this to only search distances
    # above 5 km or so, and return "worldwide" for any value below 5 km.
    #
    if user.profile.f_distance > 5:
        lat_min, lng_min, lat_max, lng_max = get_latlng_bounderies(
            user.profile.lat, user.profile.lng,
            user.profile.f_distance)
        li = li.filter(profile__lat__gte=lat_min, profile__lat__lte=lat_max,
                       profile__lng__gte=lng_min, profile__lng__lte=lng_max)

    # x only show SFW profiles?
    if user.profile.f_over_18:  # unused
        pass
        # li = li.filter(profile__over_18=True)

    # x only users with a verified email on reddit?
    if user.profile.f_has_verified_email:  # unused
        pass
        # li = li.filter(profile__has_verified_email=True)

    # 5 exclude auth user themself.
    li = li.exclude(pk=user.pk)

    # 5a. exclude banned users
    li = li.exclude(is_active=False)

    # 5b. exclude users who deleted their account (deleted last_login)
    li = li.exclude(last_login=None)

    # 5c. exclude users with low karma
    li = li.exclude(
        profile__link_karma__lte=settings.USER_MIN_LINK_KARMA,
        profile__comment_karma__lte=settings.USER_MIN_COMMENT_KARMA)

    # 6 are not already flagged by auth user ('like', 'nope', 'block')
    if not include_flagged:
        li = li.exclude(flags_received__sender=user)

    # 7 are not blocked by admin via username blocklist,
    li = li.exclude(username__in=get_blocked_usernames_list())

    # 8 have at least one picture URL,
    li = li.exclude(profile___pics='"[]"')

    if settings.DEBUG:
        print('--> li.query', li.query)

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
    BUFFER_LEN = getattr(settings, 'RESULTS_BUFFER_LEN', 500)
    # SR_LIMIT = getattr(settings, 'SR_LIMIT', 50)
    # SR_MIN_SUBS = getattr(settings, 'SR_MIN_SUBS', 100)
    # SR_MAX_SUBS = getattr(settings, 'SR_MAX_SUBS', 5000000)

    # f_ignore_sr_li
    # f_ignore_sr_max
    # f_exclude_sr_li

    # fetch users and number of same subscribed subreddits for all users
    # that are subscribed to the same subreddits than auth user; fetch a max
    # of BUFFER_LEN items. This query only touches the dtr5app_subscribed
    # table and does not requore any join with other tables.
    query_params = []
    query_string = ''

    # part 1
    query_params += []
    query_string += '''
        SELECT au.id, au.username, COUNT(r1.user_id) AS sr_count
        FROM dtr5app_subscribed r1

        INNER JOIN dtr5app_subscribed r2
            ON r1.sr_id = r2.sr_id AND r1.user_id <> r2.user_id

        INNER JOIN auth_user au
            ON r2.user_id = au.id

        INNER JOIN dtr5app_sr sr
            ON r1.sr_id = sr.id

        WHERE au.is_active IS TRUE AND last_login IS NOT NULL '''

    # part 1.1
    # if the user has set a maximum size for subreddits to be considered
    # in search. this can be used to filter all the huge default subs that
    # most redditors belong to.
    if request.user.profile.f_ignore_sr_max:
        query_params += [request.user.profile.f_ignore_sr_max]
        query_string += ''' AND sr.subscribers < %s '''

    # part 1.2
    # a list of Sr.display_name values. these subreddits should NOT be
    # considered when producing matches.
    # Subreddit names should appear as case insensitive! The f_ignore_sr_li
    # list of subreddit names is supposed to be "cleaned up" already, with
    # the appropriate lettercase of a subreddit's name.
    if request.user.profile.f_ignore_sr_li:
        query_params += request.user.profile.f_ignore_sr_li
        x = ', '.join(['%s'] * len(request.user.profile.f_ignore_sr_li))
        query_string += ''' AND sr.id NOT IN (
                                SELECT id FROM dtr5app_sr sr2
                                WHERE sr2.display_name IN (''' + x + ' )) '

    # part 1.9
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
    query_params += [request.user.id]
    query_string += ''' AND NOT (u.id IN (SELECT U1.receiver_id AS Col1
                        FROM dtr5app_flag U1 WHERE U1.sender_id = %s)) '''

    # part 7: exclude globally blocked usernames
    # li = li.exclude(username__in=get_blocked_usernames_list())
    # --> TODO: currently empty.
    pass

    # part 8: have at least one picture URL in the JSON string
    # li = li.exclude(profile___pics='[]')
    # TODO: for now, allow no-picture profiles, to make testing easier
    # query_params += []
    # query_string += ''' AND NOT (p._pics = '[]') '''

    # finish up
    query_params += [BUFFER_LEN]
    query_string += ''' ) GROUP BY r1.user_id, au.id
                          ORDER BY sr_count DESC LIMIT %s '''

    # execute the query with the collected params
    users = User.objects.raw(query_string, query_params)

    # print('='*50)
    # print(repr(users))
    # print('='*50)
    # for u in users:
    #   print('share {} subs with {}:{}'.format(u.sr_count, u.id, u.username))
    # print('='*50)

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
    if (not bt or from_iso8601(bt) + timedelta(minutes=1) < from_iso8601()):
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
