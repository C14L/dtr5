"""
All kinds of supporting functions for views and models.
"""
import pytz
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from .models import (Sr, Subscribed, Flag)
from .utils_search import search_results_buffer


def update_list_of_subscribed_subreddits(user, subscribed):
    """
    Get a list of subreddits and update the user account, adding new
    subreddits and removing deleted ones from the user's subscription
    list. Do NOT simply remove all and then add the current list,
    because that would lose the user's "is_favorite" value that is
    part of the Subscribed model.
    """
    for row in subscribed:
        sr, sr_created = Sr.objects.get_or_create(id=row['id'], defaults={
            'name': row['display_name'],  # display_name
            'created': datetime.utcfromtimestamp(
                int(row['created_utc'])).replace(tzinfo=pytz.utc),
            'url': row['url'],
            'over18': row['over18'],
            'lang': row['lang'],
            'title': row['title'],
            'display_name': row['display_name'],
            'subreddit_type': row['subreddit_type'],
            'subscribers': row['subscribers'], })
        # Add the user as subscriber to the subredit object, if that's
        # not already the case.
        sub, sub_created = Subscribed.objects.get_or_create(
            user=user, sr=sr, defaults={
                'user_is_contributor': bool(row['user_is_contributor']),
                'user_is_moderator': bool(row['user_is_moderator']),
                'user_is_subscriber': bool(row['user_is_subscriber']),
                'user_is_banned': bool(row['user_is_banned']),
                'user_is_muted': bool(row['user_is_muted']), })
        # If the user was newly added to the subreddit, count it as
        # a local user for that subreddit. (a user of the sr who is
        # also a user on this site)
        if sub_created:
            sr.subscribers_here += 1
            sr.save()
    # After adding the user to all subs, now check if they are still
    # added to subs they are no longer subbed to.
    sr_ids = [row['id'] for row in subscribed]
    to_del = Subscribed.objects.filter(user=user).exclude(sr__in=sr_ids)
    for row in to_del:
        row.sr.subscribers_here -= 1
        row.sr.save()
        row.delete()


def get_usernames_around_view_user(userbuff, view_user, n=None):
    """
    From a list of usernames and a focus user, return a list of n
    usernames to the left, and n usernames to the right of the focus
    user's username. If the list gets to one of either ends, the focus
    username shoud be centered as much as possible.

    TODO: wrap the user list around to have an "endless" list.
    """
    if not n:
        n = int(getattr(settings, 'LINKS_IN_PROFILE_HEADER', 5) / 2)
    if len(userbuff) > (2*n)+1:
        if view_user.username in userbuff:
            i = userbuff.index(view_user.username)
            min_i = i-n if i-n > 0 else 0
            max_i = i+n if i+n < len(userbuff) else len(userbuff)
            li = userbuff[min_i:max_i+1]
        else:
            # The view_user's username is not part of the usernames
            # list. This should not happen usually, but there may be
            # situations, so handle it gracefully by returning just
            # the beginning part of the usernames list.
            li = userbuff[0:(2*n)+1]
    else:
        li = userbuff
    return li


def get_user_list_around_view_user(request, view_user, n=None):
    """
    Return a list of "n" user objects, with view user as centered
    as possible.
    """
    search_results_buffer(request)
    # Fetch a short list of match usernames from session cache.
    username_list = get_usernames_around_view_user(
        request.session['search_results_buffer'], view_user)
    user_list = get_user_list_from_username_list(username_list)
    user_list = add_auth_user_latlng(request.user, user_list)
    return user_list


def get_user_list_from_username_list(username_list):
    """
    Return a list of user objects with prefetched profiles and subs,
    from a list of usernames. Important: make sure they are in the
    same order as the username_list.
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
    """Set the user's geolocation on each user list row."""
    for row in user_list:
        row.profile.set_viewer_latlng(user.profile.lat, user.profile.lng)
    return user_list


def count_matches(user):
    """Return the number of matches (mututal likes) of 'user'."""
    return User.objects.filter(
        flags_sent__receiver=user, flags_received__flag=Flag.LIKE_FLAG,
        ).filter(
        flags_received__sender=user, flags_received__flag=Flag.LIKE_FLAG
        ).distinct().count()


def get_matches_user_list(user):
    """Return a user_list with all mutual likes for 'user'."""
    user_list = list(User.objects.filter(
        flags_sent__receiver=user, flags_sent__flag=Flag.LIKE_FLAG,
        flags_received__sender=user, flags_received__flag=Flag.LIKE_FLAG))
    for x in user_list:
        c1 = x.flags_sent.get(receiver=user.pk).created
        c2 = user.flags_sent.get(receiver=x.pk).created
        setattr(x, 'matched', c1 if c1 > c2 else c2)
    user_list.sort(key=lambda row: row.matched, reverse=True)
    return user_list
