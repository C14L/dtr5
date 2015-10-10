import logging
import pytz
from time import time as unixtime
from datetime import datetime
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from simple_reddit_oauth import api
# from .models import Profile
from .models import Sr
from .models import Subscribed

logger = logging.getLogger(__name__)


def home_view(request):
    txt = '<a href="{}">Login with your Reddit account</a>'
    url = api.make_authorization_url(request)
    return HttpResponse(txt.format(url))


def me_view(request):
    template_name = "dtr5app/me.html"
    user = api.get_user(request)
    if not user:
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)
    ctx = {
        "subbed_subreddits":
            request.user.subs.all().order_by('sr__display_name'),
        "unixtime": unixtime(),
        "timeleft": request.session['expires'] - unixtime(),
    }
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


def me_update_view(request):
    if request.method != 'POST':
        txt = '<a href="{}">Login with your Reddit account</a>'
        url = api.make_authorization_url(request)
        return HttpResponse(txt.format(url))

    # Reload user's subreddit list.
    subscribed = api.get_sr_subscriber(request)
    logger.warning('User sr subscriptions data loaded: %s', len(subscribed))

    # Add them to the list of Subreddits, if they don't exist, and add
    # the relation to the user.
    for row in subscribed:
        logger.warning('--> Working on %s  %s --> %s',
                       row['id'], row['url'], row['display_name'])

        # Load the subreddit object, or create if it doesn't exist.
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

        if sr_created:
            logger.warning('----> Subreddit object created.')
        else:
            logger.warning('----> Subreddit object loaded.')

        # Add the user as subscriber to the subredit object, if that's
        # not already the case.
        sub, sub_created = Subscribed.objects.get_or_create(
            user=request.user,
            sr=sr,
            defaults={
                'user_is_contributor': bool(row['user_is_contributor']),
                'user_is_moderator': bool(row['user_is_moderator']),
                'user_is_subscriber': bool(row['user_is_subscriber']),
                'user_is_banned': bool(row['user_is_banned']),
                'user_is_muted': bool(row['user_is_muted']), })

        # If the user was actually added to the subreddit, count it as
        # a local user for that subreddit. (a user of the sr who is
        # also a user on this site)
        if sub_created:
            sr.subscribers_here += 1
            sr.save()
            logger.warning('----> Subscription object created.')
        else:
            logger.warning('----> Subscription object loaded.')

    # Reload user data from Reddit.
    reddit_user = api.get_user(request)
    logger.warning('Reddit user data loaded.')

    # Update user profile data
    request.user.profile.name = reddit_user['name']
    request.user.profile.created = datetime.utcfromtimestamp(
        int(reddit_user['created_utc'])).replace(tzinfo=pytz.utc)
    request.user.profile.updated = datetime.now().replace(tzinfo=pytz.utc)
    request.user.profile.save()

    logger.warning('Reddit user data saved locally.')
    return redirect(reverse('me_page'))


def me_locate_view(request):
    if request.method == 'POST':
        lat = float(request.POST.get('lat', 0))
        lng = float(request.POST.get('lng', 0))
        if lat and lng:
            logger.warning('--> Received lat=%s and lng=%s', lat, lng)
            request.user.profile.lat = lat
            request.user.profile.lng = lng
            request.user.profile.save()
            logger.warning('--> Written.')
    return redirect(reverse('me_page'))
