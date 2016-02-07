"""
Views only accessible to moderators (User.is_staff)
"""
from datetime import datetime

import pytz
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from dtr5app.models import Report


@staff_member_required
@require_http_methods(["GET", "POST"])
def mod_report_view(request, pk=None, template_name='dtr5app/reports.html'):
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
    kwargs = {'context_instance': RequestContext(request)}
    return render_to_response(template_name, ctx, **kwargs)


@require_http_methods(["GET", "POST"])
@staff_member_required
def mod_deluser_view(request, pk, template_name='dtr5app/mod_del_profile.html'):
    """
    For moderators to delete a user profile and ban the user.
    """
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

        # Setting an account to "is_active = False" will prevent the user from
        # using the same reddit account to sign up again. If "is_active = True"
        # then the user will be able to sign up again, using the same reddit
        # account.
        view_user.is_active = False
        view_user.save()

        kwargs = {'username': view_user.username}
        return redirect(reverse('profile_page', kwargs=kwargs))

    ctx = {'view_user': view_user}
    kwargs = {'context_instance': RequestContext(request)}
    return render_to_response(template_name, ctx, **kwargs)
