import dateutil.parser
import pytz
from time import time as unixtime
from datetime import datetime, timedelta, date
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import (JsonResponse,
                         HttpResponse,
                         HttpResponseNotFound,
                         HttpResponseBadRequest,
                         Http404)
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.utils.datastructures import MultiValueDictKeyError

from simple_reddit_oauth import api

from .models import (Subscribed, Sr, Flag, Report, Visit)

from toolbox import (force_int, force_float, set_imgur_url, get_age,
                     sr_str_to_list)

from . import utils_stats

from .utils import (add_auth_user_latlng, count_matches, get_matches_user_list,
                    get_prevnext_user, get_user_and_related_or_404,
                    get_user_list_after, update_list_of_subscribed_subreddits,
                    get_paginated_user_list, prepare_paginated_user_list,
                    add_matches_to_user_list, get_user_list_from_username_list,
                    get_matches_user_queryset, normalize_sr_names,
                    PictureInaccessibleError, assert_pic_accessible)

from .utils_search import (search_results_buffer, search_subreddit_users)


@require_http_methods(["GET", "HEAD"])
def home_view(request, template_name='dtr5app/home_anon.html'):
    if request.user.is_authenticated():
        return redirect(reverse('me_results_page'))

    ctx = {'auth_url': api.make_authorization_url(request)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
def me_view(request, template_name='dtr5app/me.html'):
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

    elif not (request.user.profile.link_karma >= LK or
              request.user.profile.comment_karma >= CK):
        # if they don't have sufficient karma, they can't sign up
        template_name = 'dtr5app/step_3_err_karma.html'
        # request.user.is_active = False
        # request.user.save()

    elif ((datetime.now().date() - request.user.profile.created) <
            timedelta(settings.USER_MIN_DAYS_REDDIT_ACCOUNT_AGE)):
        # if the account isn't old enough, they can's sign up
        template_name = 'dtr5app/step_3_err_account_age.html'
        # request.user.is_active = False
        # request.user.save()

    elif not (request.user.profile.lat and request.user.profile.lng):
        # geolocation missing, offer to auto-set it
        template_name = 'dtr5app/step_3.html'
        request.session['view_post_signup'] = True

    elif not (request.user.profile.dob and
              request.user.profile.sex and request.user.profile.about):
        # required manually input profile data is missing
        template_name = 'dtr5app/step_4.html'
        request.session['view_post_signup'] = True
        ctx['dob_min'] = '{}-{}-{}'.format(
            date.today().year-118, date.today().month, date.today().day)
        ctx['dob_max'] = '{}-{}-{}'.format(
            date.today().year-18, date.today().month, date.today().day)

    elif len(request.user.profile.pics) == 0:
        # no pics yet, ask to link one picture
        template_name = 'dtr5app/step_5.html'
        request.session['view_post_signup'] = True

    # Show "all everywhere" search results.
    # elif not request.user.profile.f_distance:
    #     # no search settings found, ask user to chose search settings
    #     template_name = 'dtr5app/step_6.html'
    #     request.session['view_post_signup'] = True

    elif (request.session.get('view_post_signup', False)):
        # user just set at least one required item. now show them the "all
        # done" page to make display of the first search result less abrupt
        template_name = 'dtr5app/step_7.html'
        request.session['view_post_signup'] = False

    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def me_account_del_view(request, template_name='dtr5app/account_del.html'):
    """delete all account data."""
    if request.method in ["POST"]:
        # fetch all of this users matches and discount them from the other
        # users match counts. currently, it can happen that a user sees a
        # match in the "upvote matches" header, but that match was from a
        # deleted user who doesn't exist anymore.
        qs = get_matches_user_queryset(request.user)
        qs = qs.prefetch_related('profile')
        for match_user in qs:
            if match_user.profile.matches_count > 0:
                match_user.profile.matches_count -= 1
                match_user.profile.save()

        # remove all data
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
    subscribed = api.get_sr_subscriber(request, settings.SR_FETCH_LIMIT)
    if subscribed:
        update_list_of_subscribed_subreddits(request.user, subscribed)

        if len(subscribed) > settings.USER_MIN_SUBSCRIBED_SUBREDDITS:
            messages.success(request, 'Subreddit list updated with {} items.'
                             .format(len(subscribed)))
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
    if settings.DEBUG:
        print('--> reddit_user: ', reddit_user)

    # make sure the types are correct!
    if reddit_user:
        # Update user profile data
        t = reddit_user['created_utc']

        p = request.user.profile
        p.name = reddit_user['name']
        p.created = datetime.utcfromtimestamp(t).replace(tzinfo=pytz.utc)
        p.updated = datetime.now().replace(tzinfo=pytz.utc)
        p.link_karma = force_int(reddit_user['link_karma'])
        p.comment_karma = force_int(reddit_user['comment_karma'])
        p.over_18 = bool(reddit_user['over_18'])
        p.hide_from_robots = bool(reddit_user['hide_from_robots'])
        p.has_verified_email = bool(reddit_user['has_verified_email'])
        p.gold_creddits = bool(reddit_user['gold_creddits'])
        p.save()

        messages.success(request, 'Profile data updated.')
    else:
        messages.warning(request, 'Could not find any user profile data.')
    # Go back to user's "me" page, the updated data should show up there.
    return redirect(reverse('me_page') + '#id_srlist')


@login_required
@require_http_methods(["GET", "POST"])
def me_locate_view(request, template_name='dtr5app/location_form.html'):
    """
    Receive latitude/longitude values found with the HTML5 geolocation API.
    The values are already "fuzzied" in the browser, so they are only the
    user's approximate location, but good enough for our purpose.
    """
    if request.method == "GET":
        ctx = {}
        return render_to_response(template_name, ctx,
                                  context_instance=RequestContext(request))
    else:
        request.user.profile.fuzzy = force_float(request.POST.get('fuzzy', 2))
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
    subreddits. TODO: currently unused
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
            # messages.error('')
            # Older browsers may submit a completely malformated dob. Ignore it
            # and carry on, no good to bother the user with this during the
            # signup flow.
            dob = datetime(year=1990, month=1, day=1).date()

        if get_age(dob) < 18:
            messages.warning(request, 'sorry, you need to be 18 or older '
                                      'to sign up on this site.')
            return redirect(reverse('me_page') + '#id_profile')

    if request.POST.get('sex', None):
        request.user.profile.sex = force_int(request.POST.get('sex'))
    if request.POST.get('about', None):
        request.user.profile.about = request.POST.get('about')
    if request.POST.getlist('lookingfor', None):
        request.user.profile.lookingfor = request.POST.getlist('lookingfor')

    if request.POST.get('pref_distance_unit', None):
        request.user.profile.pref_distance_unit = \
            request.POST.get('pref_distance_unit')

    if request.POST.get('herefor', None):
        request.user.profile.herefor = request.POST.get('herefor')

    if request.POST.get('tagline', None):  # unused
        request.user.profile.tagline = request.POST.get('tagline')
    if request.POST.get('relstatus', None):  # unused
        request.user.profile.relstatus = request.POST.get('relstatus')
    if request.POST.get('education', None):  # unused
        request.user.profile.education = request.POST.get('education')
    if request.POST.get('height', None):  # unused
        request.user.profile.height = request.POST.get('height')
    if request.POST.get('weight', None):  # unused
        request.user.profile.weight = request.POST.get('weight')
    if request.POST.get('fitness', None):  # unused
        request.user.profile.fitness = request.POST.get('fitness')

    request.user.profile.save()
    messages.success(request, 'Profile data updated.')
    _next = request.POST.get('next', '#id_profile')
    if _next.startswith('#'):
        _next = reverse('me_page') + _next

    return redirect(_next)


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
    pic_url = request.POST.get('pic_url', '')
    bg_url = request.POST.get('bg_url', '')
    if not pic_url and not bg_url:
        return HttpResponse('Please add the URL for a picture.')

    # TODO: check for valid URL schema.

    # If imgur pic, set "medium" size for normal pics, "large" for backgrounds.
    try:
        if pic_url:
            pic_url = set_imgur_url(pic_url, size='m')
            assert_pic_accessible(pic_url)
        elif bg_url:
            assert_pic_accessible(set_imgur_url(bg_url, size='l'))
    except PictureInaccessibleError as e:
        return HttpResponse(e)

    if pic_url:
        if pic_url in [x['url'] for x in request.user.profile.pics]:
            return HttpResponse('That picture already exists in your profile.')
        if len(request.user.profile.pics) >= settings.USER_MAX_PICS_COUNT:
            messages.info(request, 'oldest picture was deleted to make room '
                          'for the picture you added.')
        else:
            messages.info(request, 'picture added.')

        # prepend the new pic to make it the new "profile pic"
        request.user.profile.pics = \
            [{'url': pic_url}] + request.user.profile.pics

    if bg_url:
        request.user.profile.background_pic = bg_url
        messages.info(request, 'background picture updated.')

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
        p.f_distance = force_int(request.POST.get('f_distance'),
                                 min=0, max=21000)

    if request.POST.get('f_minage', None):
        p.f_minage = force_int(request.POST.get('f_minage'), min=18, max=99)

    if request.POST.get('f_maxage', None):
        p.f_maxage = force_int(request.POST.get('f_maxage'), min=19, max=100)

    if request.POST.get('f_hide_no_pic', None):
        if request.POST.get('f_hide_no_pic') == 'nope':
            p.f_hide_no_pic = False
        if request.POST.get('f_hide_no_pic') == 'yep':
            p.f_hide_no_pic = True

    if request.POST.get('f_over_18', None):  # unused
        p.f_over_18 = bool(request.POST.get('f_over_18'))

    if request.POST.get('f_has_verified_email', None):  # unused
        p.f_has_verified_email = bool(request.POST.get('f_has_verified_email'))

    # List of subreddit names. This needs to be cleaned for appropriate
    # letter case, so its useful in raw SQL search. Since Django has no
    # case insensivity support :( we look up the correctly cased subreddit
    # names here once, and store those as the user's search settings.
    try:
        li = sr_str_to_list(request.POST['f_ignore_sr_li'])
        p.f_ignore_sr_li = normalize_sr_names(li)
    except MultiValueDictKeyError:
        pass  # don't change the search value if not POSTed.

    try:
        p.f_ignore_sr_max = force_int(request.POST['f_ignore_sr_max'],
                                      min=100, max=123456789)
    except MultiValueDictKeyError:
        pass  # don't change the search vaue if not POSTed.

    try:
        li = sr_str_to_list(request.POST['f_exclude_sr_li'])
        p.f_exclude_sr_li = normalize_sr_names(li)
    except MultiValueDictKeyError:
        pass  # don't change the search value if not POSTed.

    request.user.profile = p

    #
    # TODO: check if model is dirty and only force a search results
    # buffer refresh if the search parameters actually changed. To
    # avoid too many searches.
    #
    request.user.profile.save()
    search_results_buffer(request, force=True)  # refresh search buffer items

    if len(request.session['search_results_buffer']) < 1:
        messages.warning(request, txt_not_found)
        return redirect(request.POST.get('next', reverse('me_results_page')))

    # messages.success(request, 'Search options updated.')
    if request.session.get('view_post_signup', False):
        return redirect(request.POST.get('next', reverse('me_results_page')))
    else:
        # x = {'username': request.session['search_results_buffer'][0]}
        # return redirect(reverse('profile_page', kwargs=x))
        return redirect(reverse('me_results_page'))


@login_required
def me_results_view(request, template_name='dtr5app/results.html'):
    """
    Show a page of search results from auth user's search buffer.

    """
    pg = int(request.GET.get('page', 1))
    search_results_buffer(request)
    li = request.session['search_results_buffer']
    li = prepare_paginated_user_list(li, pg)
    li.object_list = get_user_list_from_username_list(li.object_list)
    li.object_list = add_auth_user_latlng(request.user, li.object_list)

    ctx = {'user_list': li}
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
        return HttpResponseNotFound('user was banned')
    if not view_user.last_login:
        # user deleted their account
        raise Http404

    # Add auth user's latlng, so we can query their distance.
    view_user.profile.set_viewer_latlng(request.user.profile.lat,
                                        request.user.profile.lng)

    # Make sure there is a list of 10 pic objects, empty or not.
    setattr(view_user, 'pics_list', view_user.profile.pics[:10])
    view_user.pics_list += [None] * (10 - len(view_user.pics_list))

    # Find the SRs that auth user and view user have in common, EXCLUDING all
    # SRs that are filtered by auth users "ignore_sr_li" and "ignore_sr_max"
    # search settings.
    view_user.profile.set_common_subs(request.user.subs.all(),
                                      request.user.profile.f_ignore_sr_li,
                                      request.user.profile.f_ignore_sr_max)

    # Get the next five users to be displayed at the end of the profile page.
    user_list = get_user_list_after(request, view_user, 5)

    # Find previous and next user on the list, relative to view user.
    prev_user, next_user = get_prevnext_user(request, view_user)
    if not prev_user and user_list:
        prev_user = user_list[-1]
    if not next_user and user_list:
        next_user = user_list[0]

    # Count the profile view, unless auth user is viewing their own profile.
    if request.user.pk != view_user.pk:
        # to minimize repeated counting (in case of page relaod etc) remember
        # the last 10 profiles authuser visited and don't count them again.
        if 'last_viewed_users' not in request.session.keys():
            request.session['last_viewed_users'] = []
        try:
            request.session['last_viewed_users'].remove(view_user.pk)
        except ValueError:
            view_user.profile.views_count += 1
            view_user.profile.new_views_count += 1
            view_user.profile.save(update_fields=['views_count',
                                                  'new_views_count'])
        request.session['last_viewed_users'].append(view_user.pk)

        # remember the view for visitor history
        Visit.add_visitor_host(request.user, view_user)

    # there was an error with the "created" timestamp handling, so some were
    # set to "0", i.e. Epoch time 1970-01-01. Filter those out.
    show_created = (view_user.profile.created and
                    view_user.profile.created > date(1970, 1, 1))

    ctx = {'show_created': show_created,
           'view_user': view_user,
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
def sr_view(request, sr, template_name='dtr5app/sr.html'):
    """
    Display a list of users who are subscribed to a subreddit.
    """
    pg = int(request.GET.get('page', 1))
    view_sr = get_object_or_404(Sr, display_name__iexact=sr)
    ul = search_subreddit_users(request.user, view_sr)

    ctx = {'view_sr': view_sr,
           'user_list': get_paginated_user_list(ul, pg, request.user),
           'user_subs_all': request.user.subs.all().prefetch_related('sr')}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["POST", "GET", "HEAD"])
def me_flag_del_view(request):
    """
    Delete ALL listed flags authuser set on other users.
    """
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
    redirect to GET[next] value, if exists, or to the next user in
    session[search_results_buffer] list.

    Valid action values: 'set', 'delete'.
    Valid flag values: 'like', 'nope', 'report'.
    """
    _next = None
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
        raise Http404

    elif request.method in ['POST']:

        if action == 'set' and flag in flags.keys():
            Flag.set_flag(request.user, view_user, flag)

            if flag == 'like':
                view_user.profile.new_likes_count += 1
                view_user.profile.save(update_fields=['new_likes_count'])

                if request.user.profile.match_with(view_user):
                    # a match? then count the new match on both users'
                    # profiles.
                    request.user.profile.new_matches_count += 1
                    request.user.profile.save()
                    view_user.profile.new_matches_count += 1
                    view_user.profile.save()
                    # if authuser set a like flag, and we have a match, then
                    # show the newly matched profile again, so authuser can
                    # write them a message!
                    _next = reverse('profile_page', args={view_user.username})

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
            # delete any flag, because a user can only ever set one flag on
            # another user at the same time.
            Flag.delete_flag(request.user, view_user)
            # if this was a "remove like" or "remove nope" then display the
            # same profile again, because most likely the auth user wants to
            # change their flag.
            _next = reverse('profile_page', args={view_user.username})

        else:
            raise Http404

        # after changing a flag, always recount, because setting a flag may
        # delete another in the same process, there is no way to simply add
        # one to the match count cache.
        request.user.profile.matches_count = count_matches(request.user)
        request.user.profile.save(update_fields=['matches_count'])
        view_user.profile.matches_count = count_matches(view_user)
        view_user.profile.save(update_fields=['matches_count'])

        # Redirect the user, either to the "next profile" if there is any
        # in the search results buffer, or to the same profile if they were
        # just looking at a single profile that's maybe not in the results
        # buffer list. Or, if they ran out of results in the results buffer
        # then redirect them to the preferences page, so they can run the
        # search again and maybe fill new profiles into the results buffer.
        if _next:
            return redirect(_next)

        if len(request.session['search_results_buffer']) > 0:
            # if there are more profiles, show them.
            if view_user.username in request.session['search_results_buffer']:
                prev_user, next_user = get_prevnext_user(request, view_user)
                _next = reverse('profile_page', args={next_user.username})
                username = view_user.username
                request.session['search_results_buffer'].remove(username)
                request.session.modified = True
            else:
                username = request.session['search_results_buffer'][0]
                _next = reverse('profile_page', args={username})
        elif len(request.session['search_results_buffer']) < 1:
            messages.warning(request, 'nobody found :(')
            return redirect(reverse('me_page'))

        return redirect(request.POST.get('next', _next))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_nope_view(request):
    template_name = 'dtr5app/nopes.html'
    pg = int(request.GET.get('page', 1))
    ul = User.objects.filter(flags_received__sender=request.user,
                             flags_received__flag=Flag.NOPE_FLAG
                             ).prefetch_related('profile')
    ctx = {'user_list': get_paginated_user_list(ul, pg, request.user)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_viewed_me_view(request):
    """A list of users who recently viewed auth user's profile."""
    template_name = 'dtr5app/viewed_me.html'
    pg = int(request.GET.get('page', 1))

    # fetch last 1000 visitors list
    vl = request.user.was_visited.filter(
        hidden=False, visitor__last_login__isnull=False,
        visitor__is_active=True).order_by('-visitor').distinct('visitor')\
        .prefetch_related('visitor')\
        .values_list('visitor__username', 'created')[:1000]

    # fetch the User qs
    ul = User.objects.filter(username__in=[x[0] for x in vl])
    ul = get_paginated_user_list(ul, pg, request.user)

    # attach "visited" property to each user
    for u in ul.object_list:
        try:
            v = [x[1] for x in vl if x[0] == u.username][0]
            setattr(u, 'visit_created', v)
        except IndexError:
            setattr(u, 'visit_created', None)

    # Reset the new_views_count value
    request.user.profile.new_views_count = 0
    request.user.profile.save(update_fields=['new_views_count'])

    ctx = {'user_list': sorted(ul, key=lambda x: x.visit_created,
                               reverse=True)}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_like_view(request):
    """
    A list of likes sent by auth user to other users, and
    not /confirmed/ by them.
    """
    template_name = 'dtr5app/likes_sent.html'
    pg = int(request.GET.get('page', 1))

    # these are sent upvotes, including those that are "matches" (mutual)
    ul = User.objects.filter(
        flags_received__sender=request.user,
        flags_received__flag=Flag.LIKE_FLAG).prefetch_related('profile')
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    ctx = {'user_list': ul}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def me_recv_like_view(request):
    """Show likes sent by other users in auth user's "inbox"."""
    template_name = 'dtr5app/likes_recv.html'
    pg = int(request.GET.get('page', 1))

    # get a queryset with all profiles that are "ignored" by authuser
    nopes_qs = User.objects.filter(flags_received__sender=request.user,
                                   flags_received__flag=Flag.NOPE_FLAG)
    # fetch all users that sent an upvote to authuser and did not receive
    # a downvote (hide) from authuser.
    ul = User.objects.filter(flags_sent__receiver=request.user,
                             flags_sent__flag=Flag.LIKE_FLAG)\
                     .exclude(pk__in=nopes_qs)\
                     .prefetch_related('profile')
    ul = get_paginated_user_list(ul, pg, request.user)
    ul.object_list = add_matches_to_user_list(ul.object_list, request.user)

    # Reset the new_likes_count value
    request.user.profile.new_likes_count = 0
    request.user.profile.save(update_fields=['new_likes_count'])

    ctx = {'user_list': ul}
    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET", "HEAD"])
def matches_view(request):
    """
    Show a page with all matches (i.e. mututal 'like' flags) of auth
    user and all other users.
    """
    # Get a list user_list ordered by match time, most recent first,
    # including the additional property 'matched' with match timestamp.
    template_name = 'dtr5app/matches.html'
    # pg = int(request.GET.get('page', 1))
    user_list = get_matches_user_list(request.user)
    user_list = add_auth_user_latlng(request.user, user_list)

    #
    # TODO: pagination!!!
    #

    # Recount the total matches number to correct for countring errors.
    request.user.profile.matches_count = count_matches(request.user)
    # Reset the new_matches_count value
    request.user.profile.new_matches_count = 0
    request.user.profile.save(update_fields=['matches_count',
                                             'new_matches_count'])
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


def stats(request, template_name='dtr5app/stats.html'):

    ctx = {
        'users_by_sex': utils_stats.get_users_by_sex(),
        'likes_count': utils_stats.get_likes_count(),
        'nopes_count': utils_stats.get_nopes_count(),
        'matches_count': utils_stats.get_matches_count(),

        # active users in the past 1, 5, and 15 minutes
        'users_active_1m': utils_stats.get_active_users(1),
        'users_active_5m': utils_stats.get_active_users(5),
        'users_active_15m': utils_stats.get_active_users(15),
        'users_active_1h': utils_stats.get_active_users(60),  # past hour
        'users_active_24h': utils_stats.get_active_users(24*60),  # past 24h
        'users_active_7d': utils_stats.get_active_users(7*24*60),  # past 7d
        'users_active_30d': utils_stats.get_active_users(30*24*60),  # past 30d
        'users_active_90d': utils_stats.get_active_users(90*24*60),  # past 90d
        'users_active_1y': utils_stats.get_active_users(356*24*60),  # past 1y

        'signups_per_day': utils_stats.get_signups_per_day_for_range(
            (date.today() - timedelta(days=30)), date.today())
    }

    return render_to_response(template_name, ctx,
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["GET"])
def usermap(request, tpl='dtr5app/usermap.html', ctx={}):
    if request.is_ajax():
        west = request.GET.get('west', None)
        south = request.GET.get('south', None)
        east = request.GET.get('east', None)
        north = request.GET.get('north', None)
        t = force_int(request.GET.get('t', 0))

        if settings.DEBUG:
            print(west, north, east, south, t)

        users = User.objects.exclude(
            profile__lat__gte=-0.1, profile__lng__gte=-0.1,
            profile__lat__lte=1.1, profile__lng__lte=1.1
            ).filter(
            profile__lat__gte=south, profile__lng__gte=west,
            profile__lat__lte=north, profile__lng__lte=east,
            is_active=True, last_login__isnull=False)

        if t > 0:
            tmin = datetime.now().replace(tzinfo=pytz.utc)-timedelta(minutes=t)
            users = users.filter(profile__accessed__gte=tmin)

        users = [[u.username, u.profile.lat, u.profile.lng]
                 for u in users.prefetch_related('profile')[:250]]
        return JsonResponse({'users': users})

    return render_to_response(tpl, ctx,
                              context_instance=RequestContext(request))
