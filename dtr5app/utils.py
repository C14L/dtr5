"""
All kinds of supporting functions for views and models.
"""
import pytz
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from .models import Sr, Subscribed
from toolbox import (to_iso8601, from_iso8601)


def search_results_buffer(request, force=False):
    """
    Check if there are search results in session cache. If there are
    not, or 'force' is True, run a search and load the usernames into
    the buffer.
    """
    bt = request.session.get('search_results_buffer_time', None)
    if (not bt or from_iso8601(bt) + timedelta(days=1) < from_iso8601()):
        force = True
    bufflen = getattr(settings, 'RESULTS_BUFFER_LEN', 500)
    if force or not request.session.get('search_results_buffer', None):
        li = User.objects.all()[:bufflen].values_list('username', flat=True)
        request.session['search_results_buffer'] = list(li)
        request.session['search_results_buffer_time'] = to_iso8601()


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
