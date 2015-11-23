from django.conf import settings


def selected_settings(request):
    return {
        'DEBUG': settings.DEBUG,
        'USER_MIN_DAYS_REDDIT_ACCOUNT_AGE':
            settings.USER_MIN_DAYS_REDDIT_ACCOUNT_AGE,
        'USER_MIN_LINK_KARMA': settings.USER_MIN_LINK_KARMA,
        'USER_MIN_COMMENT_KARMA': settings.USER_MIN_COMMENT_KARMA,
    }
