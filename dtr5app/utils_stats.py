# pylint: disable=E1101

import pytz

from datetime import datetime, timedelta
from datetime import time as dt_time

from django.db.models import Count
from django.contrib.auth.models import User
from django.utils.timezone import now

from dtr5app.models import Flag


def get_users_by_sex():
    users = User.objects\
        .values('profile__sex')\
        .filter(is_active=True, last_login__isnull=False)\
        .order_by('profile__sex')\
        .annotate(Count('profile__user'))

    return [{'sex': x['profile__sex'], 'count': x['profile__user__count']} for x in users]


def get_signups_per_day(day_date, still_active=False):
    """Return the total number of new user accounts created that day. 
    Limited to accounts that are still active, if "still_active" is True.
    """
    qs = User.objects.filter(date_joined__contains=day_date)

    if still_active:
        qs = qs.filter(is_active=True, last_login__isnull=False)

    return qs.count()


def get_signups_per_day_for_range(day_from, day_until, still_active=False):
    """Return the signups per day for a range of days. Limited to 
    accounts that are still active, if "still_active" is True.
    """
    noon = dt_time(12, 0)
    d1 = datetime.combine(day_from, noon).replace(tzinfo=pytz.utc)
    d2 = datetime.combine(day_until, noon).replace(tzinfo=pytz.utc)
    qs = User.objects.filter(date_joined__gte=d1, date_joined__lte=d2)

    if still_active:
        qs = qs.filter(is_active=True, last_login__isnull=False)

    qs = qs.extra({'day': "date(date_joined)"}).values('day')
    qs = qs.annotate(Count('id')).order_by('day')
    return qs


def get_historic_users_count():
    """Return total number of user accounts ever created (including 
    deleted and blocked).
    """
    return User.objects.all().count()


def get_users_count():
    """Return total number of active users (excluding deleted and blocked).
    """
    return User.objects.filter(is_active=True, last_login__isnull=False).count()


def get_likes_count():
    """Return the total number of like Flags set.
    """
    return Flag.objects.filter(flag=Flag.LIKE_FLAG).count()


def get_nopes_count():
    """Return the total number of like Flags set.
    """
    return Flag.objects.filter(flag=Flag.NOPE_FLAG).count()


def get_matches_count():
    """Return the total number of matches (mututal likes).
    """

    return ''
    # TODO: count matches 
    #   dtr5app_flag.sender
    #   dtr5app_flag.receiver
    #   dtr5app_flag.flag


def get_active_users(mins):
    """Return number of users active over the past "mins" minutes.
    """
    min_dt = now() - timedelta(minutes=mins)
    return User.objects.filter(profile__accessed__gte=min_dt).count()
