from django.conf import settings


def selected_settings(request):
    return {
        'DEBUG': settings.DEBUG
    }
