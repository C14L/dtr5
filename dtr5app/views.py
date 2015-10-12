import dateutil.parser
import logging
import pytz
import requests  # to check image URLs for HTTO 200 responses
from time import time as unixtime
from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from simple_reddit_oauth import api

from toolbox import force_int, force_float, set_imgur_url
from .models import Sr
from .models import Subscribed
from .utils import search_results_buffer

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
        "pics": request.user.pics.all().order_by('-pk'),
        "subbed_subreddits":
            request.user.subs.all().order_by('sr__display_name'),
        "sex_choices": settings.SEX,
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
        request.user.profile.lat = force_float(request.POST.get('lat', 0.0))
        request.user.profile.lng = force_float(request.POST.get('lng', 0.0))
        request.user.profile.save()
        messages.success(request, 'Location data updated.')
        return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_favsr_view(request):
    """
    Save favorite subreddits picked by auth user from their list of
    subreddits.
    """
    sr_id_li = [x[3:] for x in request.POST.keys() if x.startswith('id_')]
    sr_li = Subscribed.objects.filter(user=request.user)
    sr_li.update(is_favorite=False)  # delete all favorites of user
    sr_li = Subscribed.objects.filter(user=request.user, sr__in=sr_id_li)
    if sr_li:
        sr_li.update(is_favorite=True)  # and set favorite on the subset
    return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_manual_view(request):
    """
    Save profile data manually input by auth user: birthdate, sex, etc.
    """
    if request.POST.get('dob', None):
        try:
            dob = dateutil.parser.parse(request.POST.get('dob', None)).date()
            request.user.profile.dob = dob
        except:
            pass
    if request.POST.get('sex', None):
        request.user.profile.sex = force_int(request.POST.get('sex'))

    request.user.profile.save()
    return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_picture_delete_view(request):
    """
    Delete one of auth user's picture URLs.
    """
    pic_url = request.POST.get('pic_url', None)
    try:
        request.user.pics.get(url=pic_url).delete()
        messages.info(request, 'Picture removed.')
    except:
        messages.info(request, 'Picture not found.')
    return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_picture_view(request):
    """
    Save the URL of a picture.
    """
    allowed_content_types = ['image/jpeg', 'image/gif', 'image/webp',
                             'image/png']
    pic_url = request.POST.get('pic_url', '')
    if not pic_url:
        return HttpResponse('Please add the URL for a picture.')
    # Check for valid URL schema.
    # ...

    # If imgur.com picture, set to "medium" size.
    pic_url = set_imgur_url(pic_url, size='m')

    # Check for HTTP 200 response on that URL, load time,
    # file size, file type, etc.
    try:
        r = requests.head(pic_url, timeout=1)  # 1 sec timeout
    except:
        return HttpResponse('The image is loading too slowly.')
    if r.status_code != 200:
        return HttpResponse('The image "{}"" can not be accessed, it returned '
                            'HTTP status code "{}".'.
                            format(pic_url, r.status_code))
    if r.headers.get('content-type', None) not in allowed_content_types:
        return HttpResponse('Not recognized as an image file. Please only '
                            'use jpg, gif, png, or webp images. Recognized '
                            'mime type was "{}".'.
                            format(r.headers.get('content-type', '')))
    if force_int(r.headers.get('content-length')) > (1024 * 512):
        return HttpResponse('The image file size ({} kiB) is too large. '
                            'Please use a smaller size (max. 500 kiB).'.
                            format(r.headers.get('content-length') / 1024))
    # Count user's pics and limit to 10 or so.
    if request.user.pics.all().count() < 10:
        request.user.pics.create(user=request.user, url=pic_url)
    else:
        return HttpResponse('You already have 10 pictures in '
                            'your profile. Please delete an old '
                            'picture, before adding another one.')
    return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_search_view(request):
    """
    Save the user search settings and redirect to search results page.
    """
    p = request.user.profile
    if request.POST.get('f_sex', None):
        p.f_sex = force_int(request.POST.get('f_sex'))
    if request.POST.get('f_distance', None):
        p.f_distance = force_int(request.POST.get('f_distance'), max=20000)
    if request.POST.get('f_minage', None):
        p.f_minage = force_int(request.POST.get('f_minage'), min=18)
    if request.POST.get('f_maxage', None):
        p.f_maxage = force_int(request.POST.get('f_maxage'), max=100)
    if request.POST.get('f_over_18', None):
        p.f_over_18 = bool(request.POST.get('f_over_18'))
    if request.POST.get('f_has_verified_email', None):
        p.f_has_verified_email = bool(request.POST.get('f_has_verified_email'))
    request.user.profile = p
    request.user.profile.save()
    # Force search buffer refresh,
    search_results_buffer(request, force=True)
    # and go to first search result, if any.
    if len(request.session['search_results_buffer']) > 0:
        return redirect(reverse('profile_page', kwargs={
            'username': request.session['search_results_buffer'][0]}))
    else:
        messages.warning(request,
                         'No redditors found that match the search options.')
        return redirect(reverse('me_page'))


def profile_view(request, username, template_name='dtr5app/profile.html'):
    search_results_buffer(request)
    view_user = get_object_or_404(User, username=username)
    userbuff = request.session['search_results_buffer']

    logger.warning('userbuff == "%s"', userbuff)

    # find 5 users to the left and 5 to the right
    if len(userbuff) < 12:
        li = userbuff
    else:
        for i in range(0, len(userbuff)):
            if userbuff[i+5] == view_user.username:
                li = userbuff[i:i+11]
                break
    user_list = User.objects.filter(username__in=li)
    ctx = {'view_user': view_user, 'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))
