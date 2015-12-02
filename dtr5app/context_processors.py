from django.conf import settings
from django.contrib.auth.models import User
from .models import Flag


def site_stats(request):
    return {
        'member_count': User.objects.all().count(),
        'like_count': Flag.objects.filter(flag=Flag.LIKE_FLAG).count(),
    }


def selected_settings(request):
    return {
        'DEBUG': settings.DEBUG,
        'CANONICAL_HOST': settings.CANONICAL_HOST,
        'ABSOLUTE_URI': request.build_absolute_uri(),

        'USER_MIN_DAYS_REDDIT_ACCOUNT_AGE':
            settings.USER_MIN_DAYS_REDDIT_ACCOUNT_AGE,
        'USER_MIN_LINK_KARMA': settings.USER_MIN_LINK_KARMA,
        'USER_MIN_COMMENT_KARMA': settings.USER_MIN_COMMENT_KARMA,

        'SEX': settings.SEX,
        'LOOKINGFOR': settings.LOOKINGFOR,
        'RESULTS_BUFFER_LEN': settings.RESULTS_BUFFER_LEN,
        'DISTANCE': settings.DISTANCE,

    }
