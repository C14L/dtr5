"""
All kinds of supporting functions for views and models.
"""
import pytz
from datetime import datetime
from django.contrib.auth.models import User
from .models import Sr, Subscribed


def search_results_buffer(request, force=False):
    """
    Check if there are search results in session cache. If there are
    not, or 'force' is True, run a search and load the usernames into
    the buffer.
    """
    if force or not request.session.get('search_results_buffer', None):
        li = User.objects.all().values_list('username', flat=True)
        request.session['search_results_buffer'] = list(li)


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
