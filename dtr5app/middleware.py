from datetime import datetime
from pytz import utc
from django.conf import settings
from django.utils.timezone import now


class UserProfileLastActiveMiddleware():
    """Set Profile.accessed to now()."""

    def process_request(self, request):
        if request.user.is_authenticated():
            request.user.profile.accessed = datetime.now().replace(tzinfo=utc)
            request.user.profile.save(update_fields=['accessed'])

        return None


class CheckSiteTemporarilyUnavailable():
    """Prevent access if settings.SITE_TEMPORARILY_UNAVAILABLE is True."""

    def process_request(self, request):
        HTTP_SERVICE_UNAVAILABLE = 503
        HTTP_SERVICE_UNAVAILABLE_REASON = 'Service Unavailable'
        html = ('<h1>oh, nose!</h1>'
                '<p>the site is temporarily unavailable for some reason or '
                'another. sorry, please come back a bit later :)</p>'
                '<h2>Possible reasons:</h2>'
                '<ul>'
                '<li>too many people, our server is too busy.</li>'
                '<li>too few people, our server fell asleep.</li>'
                '<li>we fixed the app and are updating the server.</li>'
                '<li>we did not fix the app when we should have.</li>'
                '<li>a racoon ate the server\'s poweer cable.</li>'
                '<li>...</li>'
                '</ul>')
        if settings.SITE_TEMPORARILY_UNAVAILABLE:
            return HttpResponse(content=html,
                                content_type='text/html',
                                status=HTTP_SERVICE_UNAVAILABLE,
                                reason=HTTP_SERVICE_UNAVAILABLE_REASON)
        return None
