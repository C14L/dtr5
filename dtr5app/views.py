import logging
import pytz
from time import time as unixtime
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from simple_reddit_oauth import api
# from .models import Profile
from .models import Sr
from .models import Subscribed

logger = logging.getLogger(__name__)


def home_view(request):
    if request.user.is_authenticated():
        return redirect(reverse('me_page'))
    txt = '<a href="{}">Login with your Reddit account</a>'
    url = api.make_authorization_url(request)
    return HttpResponse(txt.format(url))


def me_view(request, template_name="dtr5app/me.html"):
    if not request.user.is_authenticated():
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)
    ctx = {
        "subbed_subreddits":
            request.user.subs.all().order_by('sr__display_name'),
        "unixtime": unixtime(),
        "timeleft": request.session['expires'] - unixtime(),
    }
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@require_http_methods(["POST"])
def me_update_view(request):
    """
    Update the user profile with fresh data from user's Reddit account,
    then simply redirect to user's "me" page and add message to confirm
    the success or report failure.
    """

    # Reload user's subreddit list.
    subscribed = api.get_sr_subscriber(request)
    if subscribed:
        # Merge them into the local list of subreddits for this user.
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
            user=request.user, sr=sr, defaults={
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
        messages.success(request, 'Subreddit list updated.')
    else:
        messages.warning(request, 'Could not find any subscribed subreddits.')

    # Reload user profile data from Reddit.
    reddit_user = api.get_user(request)
    if reddit_user:
        # Update user profile data
        request.user.profile.name = reddit_user['name']
        request.user.profile.created = datetime.utcfromtimestamp(
            int(reddit_user['created_utc'])).replace(tzinfo=pytz.utc)
        request.user.profile.updated = datetime.now().replace(tzinfo=pytz.utc)
        request.user.profile.save()
        messages.success(request, 'Profile data updated.')
    else:
        messages.warning(request, 'Could not find any user profile data.')

    # Go back to user's "me" page, the updated data should show up there.
    return redirect(reverse('me_page'))


@require_http_methods(["GET", "POST"])
def me_locate_view(request):
    """
    Receive latitude/longitude values found with the HTML5 geolocation API.
    The values are already "fuzzied" in the browser, so they are only the
    user's approximate location, but good enough for our purpose.
    """
    if request.method == "GET":
        template_name = "dtr5app/location_form.html"
        ctx = {}
        return render_to_response(template_name, ctx,
                                  context_instance=RequestContext(request))
    else:
        request.user.profile.lat = float(request.POST.get('lat', 0))
        request.user.profile.lng = float(request.POST.get('lng', 0))
        request.user.profile.save()
        messages.success(request, 'Location data updated.')
        return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_favsr_view(request):
    """
    Save favorite subreddits picked by auth user from their list of
    subreddits.
    """
    sr_id_list = [x[3:] for x in request.POST.keys() if x.startswith('id_')]
    print('--> sr_id_list --> {}'.format(sr_id_list))
    return redirect(reverse('me_page'))


def profile_view(request, template_name='dtr5app/profile.html'):
    ctx = {}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))
