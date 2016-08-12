"""
All kinds of supporting functions for views and models.
"""
import pytz
import requests
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.http import Http404
from .models import Sr, Subscribed, Flag
from toolbox import force_int


def get_subs_for_user(user):
    if user.is_authenticated():
        return user.subs.all().prefetch_related('sr')

    return []


def prepare_paginated_user_list(user_list, page):
    """
    Receives a list and a page number, and returns the appropriate page. If
    the page doesn't exist, it raises Http404.
    """
    per_page = getattr(settings, 'USERS_PER_PAGE', 20)
    orphans = getattr(settings, 'USERS_ORPHANS', 0)

    paginated = Paginator(user_list, per_page=per_page,  orphans=orphans)
    try:
        user_page = paginated.page(page)
    except EmptyPage:  # out of range
        raise Http404
    except ValueError:  # not a number
        raise Http404

    return user_page


def get_paginated_user_list(user_list, page, user):
    """
    Return one page of a list of user objects to be handed to the template,
    complete with auth user's geolocation values attached for display of the
    distance between the two users.

    :user_list: User queryset to be paginated.
    :page: the number of the page to return.
    :user: a User instance, usually request.user, from whose geolocation the
           distances to all users the the returned page are calculated.
    """
    user_page = prepare_paginated_user_list(user_list, page)
    if user.is_authenticated():
        ul = add_auth_user_latlng(user, user_page.object_list)
        user_page.object_list = ul
    return user_page


def update_list_of_subscribed_subreddits(user, subscribed):
    """
    Get a list of subreddits and update the user account, adding new
    subreddits and removing deleted ones from the user's subscription
    list. Do NOT simply remove all and then add the current list,
    because that would lose the user's "is_favorite" value that is
    part of the Subscribed model.
    """
    for row in subscribed:
        # Fetch this subreddit onject or create it.
        sr, sr_created = Sr.objects.get_or_create(id=row['id'], defaults={
            'name': row['display_name'][:50],  # display_name
            'created': datetime.utcfromtimestamp(int(row['created_utc'])
                                                 ).replace(tzinfo=pytz.utc),
            'url': row['url'][:50],
            'over18': row['over18'],
            'lang': row['lang'],
            'title': row['title'][:100],
            'display_name': row['display_name'],
            'subreddit_type': row['subreddit_type'][:50],
            'subscribers': row['subscribers'], })

        # Add the user as subscriber to the subredit object, if that's
        # not already the case.
        default = {'user_is_contributor': bool(row['user_is_contributor']),
                   'user_is_moderator': bool(row['user_is_moderator']),
                   'user_is_subscriber': bool(row['user_is_subscriber']),
                   'user_is_banned': bool(row['user_is_banned']),
                   'user_is_muted': bool(row['user_is_muted']), }
        try:
            sub, sub_created = Subscribed.objects.get_or_create(
                user=user, sr=sr, defaults=default)

        except Subscribed.MultipleObjectsReturned:
            # There are a couple of users who have "double subscriptions" to
            # some (not all) of their subreddits. These users will cause this
            # exception whe trying to update their Subscribed list. Fetch the
            # double subscription and deleted it, then add it again.
            # TODO: fix all doubles, then fix db schema (unique_together).
            sub_created = False  # no new subreddit added
            Subscribed.objects.filter(user=user, sr=sr).delete()
            Subscribed.objects.create(user=user, sr=sr, **default)

        # If the user was newly added to the subreddit, count it as
        # a local user for that subreddit. (a user of the sr who is
        # also a user on this site)
        if sub_created:
            sr.subscribers_here += 1
            sr.save()

    # After adding the user to all subs from their new subscribed list, now
    # check if they are still added to any subs they were previously
    # subscribed to, but not anymore. That is, any subscription not part of the
    # new subscribed list.
    sr_ids = [row['id'] for row in subscribed]
    to_del = Subscribed.objects.filter(user=user).exclude(sr__in=sr_ids)
    for row in to_del:
        if row.sr.subscribers_here > 0:
            row.sr.subscribers_here -= 1
        row.sr.save()
        row.delete()


def get_user_list_after(request, view_user, n=5):
    """
    From the search buffer, return a list of "n" user objects after view_user.
    """
    buff = request.session['search_results_buffer']

    try:
        idx = buff.index(view_user.username)
    except ValueError:  # view_user is not part of buffer, begin at index 0
        return get_user_list_from_username_list(buff[:n])

    if (len(buff)-1) <= n:
        # buff minus view_user is n? then use entire list minus view_user
        return get_user_list_from_username_list(buff[:idx] + buff[idx+1:])

    usernames = buff[idx+1:idx+1+n]  # get n users after view_user
    if len(usernames) < n:  # if end-of-list was reached, wrap around
        n2 = n - len(usernames)
        usernames += buff[0:n2]
    return get_user_list_from_username_list(usernames)


def get_user_list_from_username_list(username_list):
    """
    Return a list of user objects with prefetched profiles and subs, from
    a list of usernames. Important: must be are in the same order as the
    username_list.
    """
    # Look up complete info on the users on that list.
    li = User.objects.filter(
        username__in=username_list).prefetch_related('profile', 'subs')

    user_list = []
    for x in username_list:
        for y in li:
            if y.username == x:
                user_list.append(y)
                break

    return user_list


def get_prevnext_user(request, view_user):
    """
    Return previous and next users, relative to view user, from the
    search results list of users.
    """
    username_list = request.session['search_results_buffer']
    try:
        idx = [username_list.index(row) for row in username_list
               if view_user.username == row][0]
    except IndexError:
        return None, None
    try:
        # Try one user to the right.
        next_user = username_list[idx+1]
    except IndexError:
        # End of list? Then start over with the first user, NOT of the
        # user list subset, but of the search result user list in the
        # session cache.
        next_user = username_list[0]
    except UnboundLocalError:
        # View user wasn't on the list (no idx)? Return first user.
        next_user = username_list[0]
    try:
        # Try one user to the left.
        prev_user = username_list[idx-1]
    except IndexError:
        # Beginning of list? Start over with the last user.
        prev_user = username_list[-1]
    except UnboundLocalError:
        # View user wasn't on the list (no idx)? Return first user.
        prev_user = view_user
    # Return the user objects of both.
    return (User.objects.get(username__iexact=prev_user),
            User.objects.get(username__iexact=next_user))


def add_auth_user_latlng(user, user_list):
    """
    Set the auth user's geolocation on each user list object.
    """
    for row in user_list:
        row.profile.set_viewer_latlng(user.profile.lat, user.profile.lng)
    return user_list


def count_matches(user):
    """
    Return the number of matches (mututal likes) of User :user:.
    """
    return get_matches_user_queryset(user).distinct().count()


def get_matches_user_queryset(user):
    """
    Return a queryset that finds all matches for user.
    """
    return User.objects.filter(
        flags_sent__receiver=user, flags_sent__flag=Flag.LIKE_FLAG,
        flags_received__sender=user, flags_received__flag=Flag.LIKE_FLAG)


def get_matches_user_list(user):
    """
    Return a user_list with all mutual likes for 'user'.
    """
    user_list = list(get_matches_user_queryset(user))
    for x in user_list:
        # set the datetime they matched
        c1 = x.flags_sent.get(receiver=user.pk).created
        c2 = user.flags_sent.get(receiver=x.pk).created
        setattr(x, 'matched', c1 if c1 > c2 else c2)
        setattr(x, 'flag_created', x.matched)  # need for serializer
    user_list.sort(key=lambda row: row.matched, reverse=True)
    return user_list


def add_likes_sent(user_list, user):
    """
    Look at it from the perspective of :user: and add a "is_like_sent"
    attribut to all User objects in the user_list list who
    received a "like" from :user:.

    :user_list: a list of User objects.
    :user: a single User object.
    """
    if user.is_authenticated():
        li = User.objects.filter(username__in=[x.username for x in user_list],
                                 flags_received__sender=user,
                                 flags_received__flag=Flag.LIKE_FLAG
                                 ).values_list('username', flat=True)
        for x in user_list:
            setattr(x, 'is_like_sent', x.username in li)

    return user_list


def add_likes_recv(user_list, user):
    """
    Look at it from the perspective of :user: and add a "is_like_recv"
    attribut to all User objects in the user_list list who
    sent a "like" to :user:.

    :user_list: a list of User objects.
    :user: a single User object.
    """
    if user.is_authenticated():
        li = User.objects.filter(username__in=[x.username for x in user_list],
                                 flags_sent__receiver=user,
                                 flags_sent__flag=Flag.LIKE_FLAG
                                 ).values_list('username', flat=True)
        for x in user_list:
            setattr(x, 'is_like_recv', x.username in li)

    return user_list


def add_matches_to_user_list(user_list, user):
    """
    Add a "is_match" attribut to all User objects in the user_list list
    who are a match (mutual like) with user and return the user_list.
    """
    if user.is_authenticated():
        li = [x.username for x in user_list]
        qs = get_matches_user_queryset(user).filter(username__in=li)
        li = [x.username for x in qs]
        for x in user_list:
            setattr(x, 'is_match', x.username in li)

    return user_list


def get_user_and_related_or_404(username, *args):
    """
    Like Django's get_object_or_404() but for User objects, and it prefetches
    the related items from the :*args: list.

    :username: either str (User.username) or int (User.id).
    """
    if isinstance(username, str):
        q = {'username__iexact': username}
    elif isinstance(username, int):
        q = {'pk': username}
    else:
        raise Http404
    try:
        return User.objects.prefetch_related(*args).get(**q)
    except User.DoesNotExist:
        raise Http404


def normalize_sr_names(li):
    """
    Receive a set of randomly cased subreddit names, and return a set of
    appropriately cased subreddit names.
    """
    sr_qs = Sr.objects.none()
    for x in li:
        sr_qs |= Sr.objects.filter(name__iexact=x)

    return sr_qs.values_list('name', flat=True)


class PictureInaccessibleError(Exception):
    pass


def assert_pic_accessible(pic_url):
    # Check for HTTP 200 response on that URL, load time,
    # file size, file type, etc.
    try:
        r = requests.head(pic_url, timeout=5)
    except:
        raise PictureInaccessibleError(
            'The image {} is loading very slowly.'.format(pic_url))

    if r.status_code == 302 and 'imgur.com' in pic_url:
        return PictureInaccessibleError(
            'The image at "{}" can not be accessed, it was <b>probably '
            'deleted on Imgur</b>.'.format(pic_url))

    if r.status_code != 200:
        return PictureInaccessibleError(
            'The image "{}"" can not be accessed, it returned HTTP status '
            'code "{}".'.format(pic_url, r.status_code))

    if r.headers.get('content-type', None) not in settings.PIC_CONTENT_TYPES:
        return PictureInaccessibleError(
            'Not recognized as an image file. Please only use jpg, gif, '
            'png, or webp images. Recognized content type was "{}".'.
            format(r.headers.get('content-type', '')))

    if force_int(r.headers.get('content-length')) > (1024 * 512):
        x = int(int(r.headers.get('content-length')) / 1024)
        return PictureInaccessibleError(
            'The image file size ({} kiB) is too large. Please use a '
            'smaller size (max. 500 kiB) to ensure that your profile '
            'page loads fast for your visitors.'.format(x))

    return True
