"""
All views that update user profile data.
"""

from datetime import datetime, timedelta, date
from time import time as unixtime

import dateutil.parser
import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from simple_reddit_oauth import api
from toolbox import force_int, force_float, get_age
from toolbox_imgur import set_imgur_url
from .models import Subscribed, Flag, Report
from .utils import get_matches_user_queryset, \
                   update_list_of_subscribed_subreddits, get_prevnext_user, \
                   get_user_and_related_or_404, PictureInaccessibleError, \
                   assert_pic_accessible, count_matches
from .utils_search import search_results_buffer, update_search_settings


@login_required
def me_view(request, template_name='dtr5app/me.html'):
    """
    Show a settings page for auth user's profile.
    """
    if not request.user.is_authenticated():
        return redirect(settings.OAUTH_REDDIT_REDIRECT_AUTH_ERROR)

    ctx = {'unixtime': unixtime(),
           'timeleft': request.session['expires'] - unixtime()}
    kwargs = {'context_instance': RequestContext(request)}

    link_karma = settings.USER_MIN_LINK_KARMA
    comment_karma = settings.USER_MIN_COMMENT_KARMA

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

    elif not (request.user.profile.link_karma >= link_karma or
              request.user.profile.comment_karma >= comment_karma):
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

    elif request.session.get('view_post_signup', False):
        # user just set at least one required item. now show them the "all
        # done" page to make display of the first search result less abrupt
        template_name = 'dtr5app/step_7.html'
        request.session['view_post_signup'] = False

    return render_to_response(template_name, ctx, **kwargs)


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
            pass
            # messages.success(request, 'Subreddit list updated with {} items.'
            #                  .format(len(subscribed)))
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
        # messages.success(request, 'Profile data updated.')
    else:
        messages.warning(request, 'Could not find any user profile data.')

    # Go back to user's "me" page, the updated data should show up there.
    if request.is_ajax():
        return HttpResponse()  # HTTP 200

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
        kwargs = {'context_instance': RequestContext(request)}
        return render_to_response(template_name, ctx, **kwargs)

    request.user.profile.fuzzy = force_float(request.POST.get('fuzzy', 2))
    request.user.profile.lat = force_float(request.POST.get('lat', 0.0))
    request.user.profile.lng = force_float(request.POST.get('lng', 0.0))
    request.user.profile.save()
    # messages.success(request, 'Location data updated.')

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

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

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

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
    # messages.success(request, 'Profile data updated.')

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

    _next = request.POST.get('next', '#id_profile')
    if _next.startswith('#'):
        _next = reverse('me_page') + _next
    return redirect(_next)


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
            # messages.info(request, 'picture added.')
            pass

        # prepend the new pic to make it the new "profile pic"
        request.user.profile.pics = \
            [{'url': pic_url}] + request.user.profile.pics

    if bg_url:
        request.user.profile.background_pic = bg_url
        messages.info(request, 'background picture updated.')

    request.user.profile.save()

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

    return redirect(reverse('me_page') + '#id_pics')


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

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

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

    update_search_settings(request)
    # TODO: check if model is dirty and only force a search results
    # buffer refresh if the search parameters actually changed. To
    # avoid too many searches.
    search_results_buffer(request, force=True)
    _next = request.POST.get('next', reverse('me_results_page'))
    if len(request.session['search_results_buffer']) < 1:
        messages.warning(request, txt_not_found)

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

    return redirect(_next)


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def me_account_del_view(request, template_name='dtr5app/account_del.html'):
    """
    Delete all account data.
    """
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

        if request.is_ajax():
            return HttpResponse()  # HTTP 200

        return redirect(request.POST.get('next', settings.LOGIN_URL))

    ctx = {}
    kwargs = {'context_instance': RequestContext(request)}
    return render_to_response(template_name, ctx, **kwargs)


@login_required
@require_http_methods(["POST", "GET", "HEAD"])
def me_flag_del_view(request, template_name = 'dtr5app/flag_del_all.html'):
    """
    Delete ALL listed flags authuser set on other users.
    """
    if request.method in ['GET', 'HEAD']:  # Return a "are you sure" page.
        ctx = {}
        kwargs = {'context_instance': RequestContext(request)}
        return render_to_response(template_name, ctx, **kwargs)

    flag_str = request.POST.get('flags', 'like,nope')
    flag_ids = [Flag.FLAG_DICT[x] for x in flag_str.split(',')]
    q = Flag.objects.filter(flag__in=flag_ids, sender=request.user)
    # count = q.count()
    q.delete()

    if Flag.FLAG_DICT['like'] in flag_ids:
        request.user.profile.matches_count = 0
        request.user.profile.save()
    # messages.info(request, '{} items deleted.'.format(count))

    if request.is_ajax():
        return HttpResponse()  # HTTP 200

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
    kwargs = {'context_instance': RequestContext(request)}
    view_user = get_user_and_related_or_404(username)
    flags = {x[1]: x[0] for x in Flag.FLAG_CHOICES}

    if request.method in ['GET', 'HEAD']:
        if action == 'set' and flag == 'report':
            # for "report profile" display a form to fill in.
            template_name = 'dtr5app/report_profile_form.html'
            ctx = {'view_user': view_user,
                   'report_reasons': Report.REASON_CHOICES}
            return render_to_response(template_name, ctx, **kwargs)

        raise Http404

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
