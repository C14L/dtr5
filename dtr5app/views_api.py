from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from dtr5app.templatetags.dtr5tags import prefdist
from dtr5app.utils import add_likes_sent, add_likes_recv, \
    add_matches_to_user_list, add_auth_user_latlng


@require_http_methods(["GET"])
def filter_members_view(request):
    usernames = request.GET.get('userlist', None).split(' ')

    if not usernames:
        return JsonResponse([])

    # Verify that userlist only contains valid usernames and limit it to not
    # more than 200 items (the number of comments shows per thread for users
    # with no Reddit Gold).
    usernames = [x for x in usernames if settings.RE_USERNAME.match(x)][:200]

    # Fetch a list of all of them and return a list of usernames found with
    # attached additional data (pic, etc).
    ul = User.objects.filter(username__in=usernames)\
                        .prefetch_related('profile')[:50]

    if request.user.is_authenticated:
        ul = add_likes_sent(ul, request.user)
        ul = add_likes_recv(ul, request.user)
        ul = add_matches_to_user_list(ul, request.user)

        ul = add_auth_user_latlng(request.user, ul)

    response_data = []
    for user in ul:
        item = {'name': user.username,
                'pic': user.profile.pics[0]['url'] if user.profile.pics else '',
                'sex_symbol': user.profile.get_sex_symbol(),
                'sex': user.profile.get_sex_display(),
                'age': user.profile.get_age(), }

        if request.user.is_authenticated:
            item['is_like_sent'] = user.is_like_sent
            item['is_like_recv'] = user.is_like_recv
            item['is_match'] = user.is_match
            item['dist'] = prefdist(user.profile.get_distance(), request.user)

        response_data.append(item)

    return JsonResponse({'userlist': response_data})
