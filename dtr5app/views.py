import dateutil.parser
import logging
import pytz
import requests  # to check image URLs for HTTO 200 responses
from time import time as unixtime
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage  #, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import (HttpResponse,
                         HttpResponseNotFound,
                         HttpResponseBadRequest,
                         HttpResponseForbidden)
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from simple_reddit_oauth import api

from toolbox import force_int, force_float, set_imgur_url
from .models import Subscribed, Sr, Flag, Report
from .utils import (add_auth_user_latlng,
                    count_matches,
                    get_matches_user_list,
                    get_prevnext_user,
                    get_user_and_related_or_404,
                    get_user_list_after,
                    update_list_of_subscribed_subreddits)
from .utils_search import (search_results_buffer,
                           search_subreddit_users)

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "HEAD"])
def home_view(request):
    if request.user.is_authenticated():
        return redirect(reverse('me_search_page'))

    template_name = 'dtr5app/home_anon.html'
    ctx = {'auth_url': api.make_authorization_url(request)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def me_view(request, template_name="dtr5app/me.html"):
    """Show a settings page for auth user's profile."""
    if not request.user.is_authenticated():
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)

    ctx = {'sex_choices': settings.SEX,
           'lookingfor_choices': settings.LOOKINGFOR,
           'unixtime': unixtime(),
           'timeleft': request.session['expires'] - unixtime(),
           'USER_MAX_PICS_COUNT': settings.USER_MAX_PICS_COUNT}

    LK = settings.USER_MIN_LINK_KARMA
    CK = settings.USER_MIN_COMMENT_KARMA

    # Check if the user has filled in the basics of their profile. If
    # they haven't, show special pages for it.
    if not request.user.subs.all():
        # the user has no subs in their profile, offer to load them
        template_name = 'dtr5app/step_2.html'
        request.session['view_post_signup'] = True
    elif not request.user.profile.created:
        # the user reddit profile is incomplete, download it again
        # template_name = 'dtr5app/step_3_something.html'
        template_name = 'dtr5app/step_2.html'
        request.session['view_post_signup'] = True
    elif not (request.user.profile.link_karma > LK or
            request.user.profile.comment_karma > CK):
        # if they don't have sufficient karma, they can't sign up
        template_name = 'dtr5app/step_3_err_karma.html'
        request.user.is_active = False
        request.user.save()
    elif ((datetime.now().date() - request.user.profile.created) <
            timedelta(settings.USER_MIN_DAYS_REDDIT_ACCOUNT_AGE)):
        # if the account isn't old enough, they can's sign up
        template_name = 'dtr5app/step_3_err_account_age.html'
        request.user.is_active = False
        request.user.save()
    elif not (request.user.profile.lat and request.user.profile.lng):
        # geolocation missing, offer to auto-set it
        template_name = 'dtr5app/step_3.html'
        request.session['view_post_signup'] = True
    elif not (request.user.profile.dob and
              request.user.profile.sex and request.user.profile.about):
        # required manually input profile data is missing
        template_name = 'dtr5app/step_4.html'
        request.session['view_post_signup'] = True
    elif len(request.user.profile.pics) == 0:
        # no pics yet, ask to link one picture
        template_name = 'dtr5app/step_5.html'
        request.session['view_post_signup'] = True
    elif not (request.user.profile.f_distance):
        # no search settings found, ask user to chose search settings
        template_name = 'dtr5app/step_6.html'
        request.session['view_post_signup'] = True
    elif (request.session.get('view_post_signup', False)):
        # user just set at least one required item. now show them the "all
        # done" page to make display of the first search result less abrupt
        template_name = 'dtr5app/step_7.html'
        request.session['view_post_signup'] = False

    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def me_account_del_view(request, template_name="dtr5app/account_del.html"):
    """delete all account data."""
    if request.method in ["POST"]:
        request.user.profile.reset_all_and_save()
        request.user.subs.all().delete()
        request.user.flags_sent.all().delete()
        request.user.flags_received.all().delete()
        # if user's last_login is None means they have not activated their
        # account or have deleted it. either way, treat it as if it doesn't
        # exist.
        request.user.last_login = None  # can be None since dj 1.8
        # request.user.date_joined = None  # can't be None, so leave it
        #
        # Setting an account to "is_active = False" will prevent the user from
        # using the same reddit account to sign up again. If "is_active = True"
        # then the user will be able to sign up again, using the same reddit
        # account. ~~request.user.is_active = False~~
        #
        request.user.save()
        api.delete_token(request)
        messages.success(request, 'All account data was deleted.')
        return redirect(request.POST.get('next', settings.LOGIN_URL))
    ctx = {}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
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

        if len(subscribed) > settings.USER_MIN_SUBSCRIBED_SUBREDDITS:
            messages.success(request, 'Subreddit list updated.')
        else:
            messages.success(request, 'Subreddit list updated, but you are '
                             'only subscribed to {} subreddits. Find some '
                             'more that interest you for better results '
                             'here :)'.format(len(subscribed)))
    else:
        messages.warning(request, 'Could not find any subscribed subreddits. '
                         'Most likely, because you are still only subscribed '
                         'to the default subs and have not yet picked your '
                         'own selection.')

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
    return redirect(reverse('me_page') + '#id_srlist')


@login_required
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
        return redirect(reverse('me_page') + '#id_geolocation')


@login_required
@require_http_methods(["POST"])
def me_favsr_view(request):
    """
    Save favorite subreddits picked by auth user from their list of
    subreddits.
    """
    sr_id_li = [x[3:] for x in request.POST.keys() if x.startswith('id_')]
    if len(sr_id_li) > settings.SR_FAVS_COUNT_MAX:
        sr_id_li = sr_id_li[:settings.SR_FAVS_COUNT_MAX]  # limit nr of favs
        messages.warning(request, 'There is a maximum of {} favorites '
                         'subreddits.'.format(settings.SR_FAVS_COUNT_MAX))
    sr_li = Subscribed.objects.filter(user=request.user)
    sr_li.update(is_favorite=False)  # delete all favorites of user
    sr_li = Subscribed.objects.filter(user=request.user, sr__in=sr_id_li)
    if sr_li:
        sr_li.update(is_favorite=True)  # and set favorite on the subset
        # messages.success(request, 'Favorite subreddits updated.')
    return redirect(reverse('me_page'))


@login_required
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

    if request.POST.get('tagline', None):
        request.user.profile.tagline = request.POST.get('tagline')
    if request.POST.getlist('lookingfor', None):
        request.user.profile.lookingfor = request.POST.getlist('lookingfor')
    if request.POST.get('relstatus', None):
        request.user.profile.relstatus = request.POST.get('relstatus')
    if request.POST.get('education', None):
        request.user.profile.education = request.POST.get('education')
    if request.POST.get('height', None):
        request.user.profile.height = request.POST.get('height')
    if request.POST.get('weight', None):
        request.user.profile.weight = request.POST.get('weight')
    if request.POST.get('fitness', None):
        request.user.profile.fitness = request.POST.get('fitness')

    request.user.profile.save()
    messages.success(request, 'Profile data updated.')
    return redirect(reverse('me_page') + '#id_profile')


@login_required
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
    return redirect(reverse('me_page') + '#id_pics')


@login_required
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

    # TODO: check for valid URL schema.

    # If imgur.com picture, set to "medium" size.
    pic_url = set_imgur_url(pic_url, size='m')
    # Check for HTTP 200 response on that URL, load time,
    # file size, file type, etc.
    try:
        r = requests.head(pic_url, timeout=5)  # ? sec timeout
    except:
        return HttpResponse(
            'The image {} is loading too slowly.'.format(pic_url))
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
    if pic_url in [x['url'] for x in request.user.profile.pics]:
        return HttpResponse('That picture already exists in your profile.')

    if len(request.user.profile.pics) >= settings.USER_MAX_PICS_COUNT:
        messages.info(request, 'oldest picture was deleted to make room for '
                               'the picture you added.')
    # prepend the new pic to make it the new "profile pic"
    request.user.profile.pics = [{'url': pic_url}] + request.user.profile.pics
    request.user.profile.save()
    return redirect(reverse('me_page') + '#id_pics')


@login_required
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
    if (request.session.get('view_post_signup', False)):
        return redirect(request.POST.get('next', reverse('me_page')))
    else:
        x = {'username': request.session['search_results_buffer'][0]}
        return redirect(reverse('profile_page', kwargs=x))


@login_required
def sr_view(request, sr, template_name='dtr5app/sr.html'):
    """Display a list of users who are subscribed to a subreddit."""
    PER_PAGE = getattr(settings, 'SR_USERS_PER_PAGE', 20)
    view_sr = get_object_or_404(Sr, display_name=sr)
    user_subs_all = request.user.subs.all().prefetch_related('sr')
    # fetch sr users, then paginate and display some 15 or so per page.
    user_list = search_subreddit_users(request, view_sr)
    user_list = user_list.prefetch_related('profile', 'subs')
    paginated = Paginator(user_list, per_page=PER_PAGE,  orphans=2)
    try:
        user_page = paginated.page(int(request.GET.get('page', 1)))
    except EmptyPage:  # out of range
        return HttpResponseNotFound()
    except ValueError:  # not a number
        return HttpResponseNotFound()
    user_list = add_auth_user_latlng(request.user, user_page.object_list)
    user_page.object_list = user_list

    ctx = {'view_sr': view_sr,
           'user_list': user_page,
           'user_count': paginated.count,
           'user_subs_all': user_subs_all}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def profile_view(request, username, template_name='dtr5app/profile.html'):
    """
    Display the complete profile of one user, together with "like" and "nope"
    buttons, unless auth user is viewing their own profile.
    """
    view_user = get_user_and_related_or_404(username, 'profile', 'subs')

    if not view_user.is_active:
        # user was banned
        return HttpResponseNotFound('404 - user was banned')
    if not view_user.last_login or not view_user.profile.pics:
        # user deleted their account
        return HttpResponseNotFound('404 - user does not exist')

    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat,
                                        request.user.profile.lng)
    # Make sure there is a list of 10 pic objects, empty or not.
    setattr(view_user, 'pics_list', view_user.profile.pics[:10])
    view_user.pics_list += [None] * (10 - len(view_user.pics_list))
    # Find the subs that auth user and view user have in common.
    view_user.profile.set_common_subs(request.user.subs.all())
    # Get the next five users to be displayed at the end of the profile page.
    user_list = get_user_list_after(request, view_user, 5)
    # Find previous and next user on the list, relative to view user.
    prev_user, next_user = get_prevnext_user(request, view_user)
    # Count the profile view, unless auth user is viewing their own profile.
    if request.user.pk != view_user.pk:
        view_user.profile.views_count += 1
        view_user.profile.save()

    ctx = {'view_user': view_user,
           'is_match': request.user.profile.match_with(view_user),
           'is_like': request.user.profile.does_like(view_user),
           'is_nope': request.user.profile.does_nope(view_user),
           'lookingfor_choices': settings.LOOKINGFOR,
           'user_list': user_list,
           'prev_user': prev_user,
           'next_user': next_user}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["POST", "GET", "HEAD"])
def me_flag_del_view(request):
    """Delete all listed flags authuser set on other users."""
    if request.method in ['GET', 'HEAD']:
        # Return a "are you sure" page.
        template_name = 'dtr5app/flag_del_all.html'
        ctx = {}
        return render_to_response(template_name, ctx,
                                  context_instance=RequestContext(request))
    elif request.method in ['POST']:
        flag_str = request.POST.get('flags', 'like,nope')
        flag_ids = [Flag.FLAG_DICT[x] for x in flag_str.split(',')]
        q = Flag.objects.filter(flag__in=flag_ids, sender=request.user)
        count = q.count()
        q.delete()
        if Flag.FLAG_DICT['like'] in flag_ids:
            request.user.profile.matches_count = 0
            request.user.profile.save()
        messages.info(request, '{} items deleted.'.format(count))
        return redirect(reverse('me_page'))


@login_required
@require_http_methods(["POST", "GET", "HEAD"])
def me_flag_view(request, action, flag, username):
    """
    Let auth user set a flag for their relation to view user. Then
    redirect to the next user in session[search_results_buffer] list.

    Valid action values: 'set', 'delete'.
    Valid flag values: 'like', 'nope', 'report'.
    """
    view_user = get_user_and_related_or_404(username)
    flags = {x[1]: x[0] for x in Flag.FLAG_CHOICES}

    if request.method in ['GET', 'HEAD']:
        if action == 'set' and flag == 'report':
            # for "report profile" display a form to fill in.
            template_name = 'dtr5app/report_profile_form.html'
            ctx = {'view_user': view_user,
                   'report_reasons': Report.REASON_CHOICES}
            return render_to_response(template_name, ctx,
                                      context_instance=RequestContext(request))
        return HttpResponseNotFound()

    elif request.method in ['POST']:
        if action == 'set' and flag in flags.keys():
            Flag.set_flag(request.user, view_user, flag)

            if flag == 'like':
                # if "like", then check for both users their match count
                request.user.profile.matches_count = \
                    count_matches(request.user)
                request.user.profile.save()
                view_user.profile.matches_count = count_matches(view_user)
                view_user.profile.save()
            if flag == 'report':
                # also create an entry in Report for the moderator
                reason = request.POST.get('reason', None)
                details = request.POST.get('details', None)
                if not reason:
                    return HttpResponseBadRequest('please select a reason for '
                                                  'reporting this profile.')
                Report.objects.create(sender=request.user, receiver=view_user,
                                      reason=reason, details=details)
                messages.info(request, '{} was reported to the moderators.'
                              .format(view_user.username))

        elif action == 'delete' and flag in flags.keys():
            Flag.delete_flag(request.user, view_user)
            # if this was a "remove like" or "remove nope" then display the
            # same profile again, because most likely the auth user wants to
            # change their flag.
            return redirect(reverse('profile_page',
                                    args={view_user.username}))
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
                request.session[
                    'search_results_buffer'].remove(view_user.username)
                request.session.modified = True
            else:
                username = request.session['search_results_buffer'][0]
                _next = reverse('profile_page', args={username})
        elif len(request.session['search_results_buffer']) < 1:
            messages.warning(request, 'Nobody found. Try searching again!')
            return redirect(reverse('me_page'))

        return redirect(request.POST.get('next', _next))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_nope_view(request, template_name='dtr5app/nopes.html'):
    user_list = User.objects.filter(flags_received__sender=request.user,
                                    flags_received__flag=Flag.NOPE_FLAG)
    user_list = user_list.prefetch_related('profile')
    user_list = add_auth_user_latlng(request.user, user_list)
    ctx = {'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_like_view(request, template_name='dtr5app/likes.html'):
    user_list = User.objects.filter(flags_received__sender=request.user,
                                    flags_received__flag=Flag.LIKE_FLAG)
    user_list = user_list.prefetch_related('profile')
    user_list = add_auth_user_latlng(request.user, user_list)
    ctx = {'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def matches_view(request, template_name='dtr5app/matches.html'):
    """
    Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    user_list = get_matches_user_list(request.user)
    user_list = add_auth_user_latlng(request.user, user_list)
    request.user.profile.matches_count = count_matches(request.user)
    request.user.profile.save()
    ctx = {'user_list': user_list}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@staff_member_required
@require_http_methods(["GET", "POST"])
def mod_report_view(request, pk=None):
    """
    For staff users to review reported profiles. If a pk is given on a POST,
    set that report to "resolved".
    """
    show = request.POST.get('show', None) or request.GET.get('show', 'open')

    if request.method in ['POST']:
        # toggle the resove state of the report.
        report = get_object_or_404(Report, pk=pk)
        if report.resolved:
            report.resolved = None
        else:
            report.resolved = datetime.now().replace(tzinfo=pytz.utc)
        report.save()
        # then show the same list, either "open" or "resolved"
        return redirect(reverse('mod_report_page') + '?show=' + show)

    template_name = 'dtr5app/reports.html'
    li = Report.objects.prefetch_related('sender', 'receiver')
    if show == 'resolved':
        # show list of old resolved reports
        li = li.filter(resolved__isnull=False).order_by('-resolved')
    else:
        # or a list of fresh open reports
        li = li.filter(resolved__isnull=True).order_by('-created')

    paginator = Paginator(li, per_page=100)
    try:
        reports = paginator.page(int(request.GET.get('page', 1)))
    except EmptyPage:  # out of range
        return HttpResponseNotFound()
    except ValueError:  # not a number
        return HttpResponseNotFound()

    ctx = {'reports': reports, 'show': show}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@staff_member_required
def mod_deluser_view(request, pk):
    """for moderators to delete a user profile and ban the user"""
    view_user = get_object_or_404(User, pk=pk)

    if request.method in ["POST"]:
        view_user.profile.reset_all_and_save()
        view_user.subs.all().delete()
        view_user.flags_sent.all().delete()
        view_user.flags_received.all().delete()
        # if user's last_login is None means they have not activated their
        # account or have deleted it. either way, treat it as if it doesn't
        # exist. ~~view_user.last_login = None~~
        # view_user.date_joined = None  # can't be None, so leave it
        #
        # Setting an account to "is_active = False" will prevent the user from
        # using the same reddit account to sign up again. If "is_active = True"
        # then the user will be able to sign up again, using the same reddit
        # account.
        view_user.is_active = False
        view_user.save()
        kwargs = {'username': view_user.username}
        return redirect(reverse('profile_page', kwargs=kwargs))

    template_name = 'dtr5app/mod_del_profile.html'
    ctx = {'view_user': view_user}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))
