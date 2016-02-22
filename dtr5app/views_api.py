from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def filter_members_view(request):
    userlist = request.GET.get('userlist', None).split(' ')

    if not userlist:
        return JsonResponse([])

    # Verify that userlist only contains valid usernames
    # and limit it to not more than 100 items.
    userlist = [x for x in userlist if settings.RE_USERNAME.match(x)][:100]

    # Fetch a list of all of them and return a list of usernames found with
    # attached additional data (pic, etc).
    users = User.objects.filter(username__in=userlist)\
                        .prefetch_related('profile')
    userlist = []
    for user in users:
        if user.profile.pics:
            pic = user.profile.pics[0]['url']
        else:
            pic = ''

        userlist.append({'name': user.username, 'pic': pic,
                         'sex_symbol': user.profile.get_sex_symbol(),
                         'sex': user.profile.get_sex_display(),
                         'age': user.profile.get_age(), })

    return JsonResponse({'userlist': userlist})
