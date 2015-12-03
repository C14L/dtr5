from django.db.models import Count
from django.contrib.auth.models import User
from dtr5app.models import Flag


def get_users_by_sex():
    users = User.objects.values('profile__sex')\
                        .filter(is_active=True, last_login__isnull=False)\
                        .order_by('profile__sex')\
                        .annotate(Count('profile__user'))

    return [{'sex': x['profile__sex'],
             'count': x['profile__user__count']} for x in users]


def get_historic_users_count():
    """
    Return total number of user accounts ever created (including deleted
    and blocked).
    """
    return User.objects.all().count()


def get_users_count():
    """Return total number of active users (excluding deleted and blocked)."""
    # return User.objects.all().count()
    return User.objects.filter(is_active=True,
                               last_login__isnull=False).count()


def get_likes_count():
    """Return the total number of like Flags set."""
    return Flag.objects.filter(flag=Flag.LIKE_FLAG).count()


def get_nopes_count():
    """Return the total number of like Flags set."""
    return Flag.objects.filter(flag=Flag.NOPE_FLAG).count()


def get_matches_count():
    """Return the total number of matches (mututal likes)."""

    return ''
    """
    TODO: count matches
    dtr5app_flag.sender
    dtr5app_flag.receiver
    dtr5app_flag.flag
    """
