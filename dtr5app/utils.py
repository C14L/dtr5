"""
All kinds of supporting functions for views and models.
"""
from django.contrib.auth.models import User


def search_results_buffer(request, force=False):
    """
    Check if there are search results in session cache. If there are
    not, or 'force' is True, run a search and load the usernames into
    the buffer.
    """
    if force or not request.session.get('search_results_buffer', None):
        li = User.objects.all().values_list('username', flat=True)
        request.session['search_results_buffer'] = list(li)
