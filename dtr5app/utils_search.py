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
from .models import (Sr)  #, Subscribed, Flag)


def search_subreddit_users(request, sr):
    """
    fetch users subscribed to this subreddit [TODO: ordered by geographic
    proximity to auth user]. return a queryset that can be paginated.
    """
    return search_users_by_options_queryset(request).filter(subs__sr=sr)


def get_blocked_usernames_list():
    """Return a list of usernames blocked by admin."""
    return []


def search_users_by_options_queryset(request, include_flagged=False):
    """
    return a User queryset that filters by search opetions and some other
    basic filters like blocked usernames, etc.

    include_flagged (bool) default False
        show users be included that were already flagged (like, nope, etc)
        by auth user?
    """
    # 1
    li = User.objects.all()
    # 2 search option: sex
    if request.user.profile.f_sex > 0:
        li = li.filter(profile__sex=request.user.profile.f_sex)
    # 3 search option: age
    dob_earliest, dob_latest = get_dob_range(request.user.profile.f_minage,
                                             request.user.profile.f_maxage)
    li = li.filter(profile__dob__gt=dob_earliest, profile__dob__lt=dob_latest)
    # 4 search option: distance
    if request.user.profile.f_distance:
        lat_min, lng_min, lat_max, lng_max = get_latlng_bounderies(
            request.user.profile.lat, request.user.profile.lng,
            request.user.profile.f_distance)
        li = li.filter(profile__lat__gte=lat_min, profile__lat__lte=lat_max,
                       profile__lng__gte=lng_min, profile__lng__lte=lng_max)
    # x only show SFW profiles?
    if request.user.profile.f_over_18:
        pass
        # li = li.filter(profile__over_18=True)
    # x only users with a verified email on reddit?
    if request.user.profile.f_has_verified_email:
        pass
        # li = li.filter(profile__has_verified_email=True)
    # 5 exclude auth user themself.
    li = li.exclude(pk=request.user.pk)
    # 6 are not already flagged by auth user ('like', 'nope', 'block')
    if not include_flagged:
        li = li.exclude(flags_received__sender=request.user)
    # 7 are not blocked by admin via username blocklist,
    li = li.exclude(username__in=get_blocked_usernames_list())
    # 8 have at least one picture URL,
    li = li.exclude(profile__pics_str='"[]"')

    return li


def get_username_list_for_search_options_only(request):
    """
    Return a list of usernames that are matches for auth user's
    selected search options.
    """
    BUFFER_LEN = getattr(settings, 'RESULTS_BUFFER_LEN', 500)
    li = search_users_by_options_queryset(request)
    return list(li[:BUFFER_LEN].values_list('username', flat=True))


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

    # fetch users and number of same subscribed subreddits for all users
    # that are subscribed to the same subreddits than auth user; fetch a max
    # of BUFFER_LEN items. This query only touches the dtr5app_subscribed
    # table and does not requore any join with other tables.
    query_string = ""
    query_params = []

    # part 1
    query_params += [request.user.id]
    query_string += '''
        SELECT au.id, au.username, COUNT(r1.user_id) AS sr_count
        FROM dtr5app_subscribed r1
        INNER JOIN dtr5app_subscribed r2
            ON r1.sr_id = r2.sr_id AND r1.user_id <> r2.user_id
        INNER JOIN auth_user au
            ON r2.user_id = au.id
        WHERE r1.user_id = %s AND au.id IN (
            SELECT id FROM auth_user u
            INNER JOIN dtr5app_profile p ON u.id = p.user_id
            WHERE 1=1 '''

    # part 2: sex
    if request.user.profile.f_sex > 0:
        # li = li.filter(profile__sex=request.user.profile.f_sex)
        pass

    # part 3: date of birth
    dob_earliest, dob_latest = get_dob_range(request.user.profile.f_minage,
                                             request.user.profile.f_maxage)
    query_params += [dob_earliest, dob_latest]
    query_string += ''' AND p.dob > %s AND p.dob < %s '''

    # part 4: lat/lng
    # li = li.filter(profile__lat__gte=lat_min, profile__lat__lte=lat_max,
    #                profile__lng__gte=lng_min, profile__lng__lte=lng_max)
    if request.user.profile.f_distance:
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
    # li = li.exclude(profile__pics_str='[]')
    # query_params += []
    query_string += ''' AND NOT (p.pics_str = '[]') '''

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
    if (not bt or from_iso8601(bt) + timedelta(days=1) < from_iso8601()):
        force = True  # if buffer is old, force refresh
    if request.session.get('search_results_buffer', None) is None:
        force = True  # no buffer ever set, then do a search
    if force:
        request.session['search_results_buffer'] = search_users(request)
        request.session['search_results_buffer_time'] = to_iso8601()
        request.session.modified = True
