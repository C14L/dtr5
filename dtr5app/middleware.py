from os.path import join, exists
from datetime import datetime
from pytz import utc
from django.conf import settings
from django.utils.timezone import now
from django.http import HttpResponse


def return_site_offline_response():
        HTTP_SERVICE_UNAVAILABLE = 503
        HTTP_SERVICE_UNAVAILABLE_REASON = 'Service Unavailable'
        html = (
            '<h1>oh, nose!</h1>'
            '<p>the site is temporarily unavailable for some reason or '
            'another. sorry, please come back a bit later :)</p>'
            '<h2>Possible reasons:</h2>'
            '<ul>'
            '<li>too many people, our server is too busy.</li>'
            '<li>too few people, our server fell asleep.</li>'
            '<li>we fixed the app and are updating the server.</li>'
            '<li>we did not fix the app when we should have.</li>'
            '<li>a racoon ate the server\'s power cable.</li>'
            '<li>...</li>'
            '</ul>'
            '<p>anyways, this is not a pic of our server:</p>'
            '<p><a href="https://imgur.com/GaE4R3fm">'
            '<img src="https://i.imgur.com/GaE4R3fm.jpg" alt="">'
            '</a></p>')
        return HttpResponse(content=html,
                            content_type='text/html',
                            status=HTTP_SERVICE_UNAVAILABLE,
                            reason=HTTP_SERVICE_UNAVAILABLE_REASON)


class CheckSiteUnavailableIfSiteIsOnlineNotFound():
    """
    only in production, verify that the file 'SITE_IS_ONLINE' exists in the
    site's root dir, for example '/var/www/example.com/SITE_IS_ONLINE'.
    """
    def process_request(self, request):
        # use a file in parent dir as a switch.

        if exists(join(settings.BASE_DIR, '../../SITE_IS_ONLINE')):
            return None
        else:
            return return_site_offline_response()


class CheckSiteTemporarilyUnavailable():
    """Prevent access if settings.SITE_TEMPORARILY_UNAVAILABLE is True."""

    def process_request(self, request):
        if settings.SITE_TEMPORARILY_UNAVAILABLE:
            return return_site_offline_response()
        else:
            return None


class UserProfileLastActiveMiddleware():
    """Set Profile.accessed to now()."""

    def process_request(self, request):
        if request.user.is_authenticated():
            request.user.profile.accessed = datetime.now().replace(tzinfo=utc)
            request.user.profile.save(update_fields=['accessed'])

        return None
