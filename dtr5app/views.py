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
from django.http import (HttpResponse,
                         HttpResponseNotFound)
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from simple_reddit_oauth import api

from toolbox import force_int, force_float, set_imgur_url
from .models import Subscribed, Sr, Flag
from .utils import (search_results_buffer,
                    update_list_of_subscribed_subreddits,
                    get_user_list_around_view_user,
                    get_prevnext_user,
                    add_auth_user_latlng,
                    get_matches_user_list, count_matches)

logger = logging.getLogger(__name__)


def home_view(request):
    if request.user.is_authenticated():
        return redirect(reverse('me_search_page'))

    template_name = 'dtr5app/home_anon.html'
    ctx = {'auth_url': api.make_authorization_url(request)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


def me_view(request, template_name="dtr5app/me.html"):
    """Show a settings page for auth user's profile."""
    if not request.user.is_authenticated():
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)
    ctx = {'sex_choices': settings.SEX, 'unixtime': unixtime(),
           'timeleft': request.session['expires'] - unixtime()}
    # Check if the user has filled on the basics of their profile. If
    # they haven't, show special pages for it.
    if not request.user.subs.all():
        return render_to_response('dtr5app/step_2.html', ctx,
                                  context_instance=RequestContext(request))
    if not (request.user.profile.lat and request.user.profile.lng):
        return render_to_response('dtr5app/step_3.html', ctx,
                                  context_instance=RequestContext(request))
    if not (request.user.profile.dob and
            request.user.profile.sex and request.user.profile.about):
        return render_to_response('dtr5app/step_4.html', ctx,
                                  context_instance=RequestContext(request))
    if len(request.user.profile.pics) == 0:
        return render_to_response('dtr5app/step_5.html', ctx,
                                  context_instance=RequestContext(request))
    if not (request.user.profile.f_distance):
        return render_to_response('dtr5app/step_6.html', ctx,
                                  context_instance=RequestContext(request))
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@require_http_methods(["POST"])
def me_update_view(request):
    """
    Update the user profile with fresh data from user's Reddit account,
    then simply redirect to user's "me" page and add message to confirm
    the success or report failure.
    """
    # Reload user's subreddit list from reddit.
    subscribed = api.get_sr_subscriber(request)
    if subscribed:
        update_list_of_subscribed_subreddits(request.user, subscribed)
        if len(subscribed) > 10:
            messages.success(request, 'Subreddit list updated.')
        else:
            messages.success(request, 'Subreddit list updated, but you are onl'
                                      'y subbed to {} subreddits. Find some mo'
                                      're that interest you for better results'
                                      ' here :)'.format(len(subscribed)))
    else:
        messages.warning(request, 'Could not find any subscribed subreddits. M'
                                  'ost likely, because you are still only subs'
                                  'cribed to the default subs and have not yet'
                                  ' picked your own selection.')

    # Reload user profile data from Reddit.
    reddit_user = api.get_user(request)
    if reddit_user:
        # Update user profile data
        t = int(reddit_user['created_utc'])
        p = request.user.profile
        p.name = reddit_user['name']
        p.created = datetime.utcfromtimestamp(t).replace(tzinfo=pytz.utc)
        p.updated = datetime.now().replace(tzinfo=pytz.utc)
        p.link_karma = reddit_user['link_karma']
        p.comment_karma = reddit_user['comment_karma']
        p.over_18 = reddit_user['over_18']
        p.hide_from_robots = reddit_user['hide_from_robots']
        p.has_verified_email = reddit_user['has_verified_email']
        p.gold_creddits = reddit_user['gold_creddits']
        p.save()
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
        messages.success(request, 'Favorite subreddits updated.')
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
    if request.POST.get('about', None):
        request.user.profile.about = request.POST.get('about')

    request.user.profile.save()
    messages.success(request, 'Profile data updated.')
    return redirect(reverse('me_page'))


@require_http_methods(["POST"])
def me_pic_del_view(request):
    """
    Delete one of auth user's picture URLs.
    """
    pic_url = request.POST.get('pic_url', None)
    try:
        request.user.profile.pics = [x for x in request.user.profile.pics
                                     if x['url'] != pic_url]
        request.user.profile.save()
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
        r = requests.head(pic_url, timeout=3)  # 3 sec timeout
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
        x = int(int(r.headers.get('content-length')) / 1024)
        return HttpResponse('The image file size ({} kiB) is too large. '
                            'Please use a smaller size (max. 500 kiB).'.
                            format(x))
    if len(request.user.profile.pics) > 9:
        return HttpResponse('You already have 10 pictures in your profile. Ple'
                            'ase delete an old one, before adding another :)')
    if pic_url in [x['url'] for x in request.user.profile.pics]:
        return HttpResponse('That picture already exists in your profile.')

    request.user.profile.pics.append({'url': pic_url})
    request.user.profile.save()
    return redirect(reverse('me_page'))


@require_http_methods(["POST", "GET", "HEAD"])
def me_search_view(request):
    """
    Save the user search settings and redirect to search results page.
    """
    txt_not_found = 'No redditors found for the search options.'

    if request.method in ["GET", "HEAD"]:
        # Find the next profile to show and redirect.
        search_results_buffer(request)
        if len(request.session['search_results_buffer']) < 1:
            messages.warning(request, txt_not_found)
            return redirect(request.POST.get('next', reverse('me_page')))
        x = {'username': request.session['search_results_buffer'][0]}
        _next = request.POST.get('next', reverse('profile_page', kwargs=x))
        return redirect(_next)

    p = request.user.profile
    p.f_sex = force_int(request.POST.get('f_sex', ''))
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
    #
    # TODO: check if model is dirty and only force a search results
    # buffer refresh if the search parameters actually changed. To
    # avoid too many searches.
    #
    request.user.profile.save()
    search_results_buffer(request, force=True)
    #
    if len(request.session['search_results_buffer']) < 1:
        messages.warning(request, txt_not_found)
        return redirect(request.POST.get('next', reverse('me_page')))
    # messages.success(request, 'Search options updated.')
    x = {'username': request.session['search_results_buffer'][0]}
    return redirect(reverse('profile_page', kwargs=x))


def sr_view(request, sr, template_name='dtr5app/sr.html'):
    """Display a list of users who are subscribed to a subreddit."""
    view_sr = get_object_or_404(Sr, display_name=sr)
    user_list = User.objects.filter(subs__sr=view_sr)[:100]\
                    .prefetch_related('profile', 'subs')
    user_list = add_auth_user_latlng(request.user, user_list)
    user_subs_all = request.user.subs.all().prefetch_related('sr')
    #
    # ... TODO
    #
    ctx = {'view_sr': view_sr,
           'user_list': user_list,
           'user_subs_all': user_subs_all}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


def profile_view(request, username, template_name='dtr5app/profile.html'):
    """
    Display the complete profile of one user, and show a list of
    other users above for the user to continue browsing.
    """
    view_user = get_object_or_404(User, username=username)
    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat,
                                        request.user.profile.lng)
    # Make sure there is a list of 10 pic objects, empty or not.
    setattr(view_user, 'pics_list', view_user.profile.pics[:10])
    view_user.pics_list += [None] * (10 - len(view_user.pics_list))
    # Find the subs that auth user and view user have in common.
    view_user.profile.set_common_subs(request.user.subs.all())
    # Get a list of user objects around view user, all with latlng.
    user_list = get_user_list_around_view_user(request, view_user)
    # Find previous and next user on the list, relative to view user.
    prev_user, next_user = get_prevnext_user(request, view_user)

    ctx = {'view_user': view_user,
           'user_list': user_list,
           'prev_user': prev_user,
           'next_user': next_user}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


def me_flag_view(request, action, flag, username):
    """
    Let auth user set a flag for their relation to view user. Then
    redirect to the next user in session[search_results_buffer] list.

    Possible flag values are 'like', 'nope', 'block'
    """
    print('--> me_flag_view(): {} {} {}'.format(action, flag, username))
    view_user = get_object_or_404(User, username=username)
    flags = {x[1]: x[0] for x in Flag.FLAG_CHOICES}

    if action == 'set' and flag in flags.keys():
        Flag.set_flag(request.user, view_user, flag)
        # For both users, check their match count.
        if flag == 'like':
            request.user.profile.matches_count = count_matches(request.user)
            request.user.profile.save()
            view_user.profile.matches_count = count_matches(view_user)
            view_user.profile.save()
    elif action == 'delete':
        return HttpResponseNotFound()
    else:
        return HttpResponseNotFound()
    # Redirect the user, either to the "next profile" if there is any
    # in the search results buffer, or to the same profile if they were
    # just looking at a single profile that's maybe not in the results
    # buffer list. Or, if they ran out of results in the results buffer
    # then redirect them to the preferences page, so they can run the
    # search again and maybe fill new profiles into the results buffer.
    if len(request.session['search_results_buffer']) > 0:
        if view_user.username in request.session['search_results_buffer']:
            prev_user, next_user = get_prevnext_user(request, view_user)
            _next = reverse('profile_page', args={next_user.username})
            request.session['search_results_buffer'].remove(view_user.username)
            request.session.modified = True
        else:
            username = request.session['search_results_buffer'][0]
            _next = reverse('profile_page', args={username})
    elif len(request.session['search_results_buffer']) < 1:
        messages.warning(request, 'Nobody found. Try searching again!')
        return redirect(reverse('me_page'))
    return redirect(request.POST.get('next', _next))


def matches_view(request, template_name='dtr5app/matches.html'):
    """
    Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    if not request.user.is_authenticated():
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)
    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    user_list = get_matches_user_list(request.user)
    user_list = add_auth_user_latlng(request.user, user_list)

    request.user.profile.matches_count = count_matches(request.user)
    request.user.profile.save()
    ctx = {'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))
