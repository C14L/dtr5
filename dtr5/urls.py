"""dtr5 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from os import path
from rest_framework.urlpatterns import format_suffix_patterns

from simple_reddit_oauth import urls as simple_reddit_oauth_urls
from dtr5app import views, views_me, views_mod, views_api


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^account/', include(simple_reddit_oauth_urls)),
    url(r'^$', views.home_view, name="home_page"),

    # Users preferences page, and URIs to POST to.
    url(r'^me/$', views_me.me_view, name="me_page"),
    url(r'^me/update/$', views_me.me_update_view, name="me_update_page"),
    url(r'^me/locate/$', views_me.me_locate_view, name="me_locate_page"),
    url(r'^me/favsr/$', views_me.me_favsr_view, name="me_favsr_page"),
    url(r'^me/manual/$', views_me.me_manual_view, name="me_manual_page"),
    url(r'^me/pic/$', views_me.me_picture_view, name="me_picture_page"),
    url(r'^me/pic/delete$', views_me.me_pic_del_view, name="me_pic_del_page"),
    url(r'^me/flag/delete$', views_me.me_flag_del_view,
        name="me_flag_del_page"),
    url(r'^me/visitors/$', views.viewed_me_view, name="me_viewed_me_page"),
    url(r'^me/upvotes_inbox$', views.likes_recv_view,
        name="me_recv_like_page"),
    url(r'^me/upvotes_sent$', views.likes_sent_view, name="me_like_page"),
    url(r'^me/nopes_sent$', views.nope_view, name="me_nope_page"),
    url(r'^me/account/delete$', views_me.me_account_del_view,
        name="me_account_del_page"),

    # Refill search results buffer if necessary are redirect.
    url(r'^search/$', views_me.me_search_view, name="me_search_page"),

    # Search results as paginated list view of user profiles
    url(r'^results/$', views.results_view, name="me_results_page"),

    # Show a list of matches (auth user and view user mutual likes).
    url(r'^matches/$', views.matches_view, name="matches_page"),

    # Show all users that subscribe to a specific subreddit.
    url(r'^r/(?P<sr>' + settings.RSTR_SR_NAME + ')/$',
        views.sr_view, name="sr_page"),

    # Show "view user"'s profile page.
    url(r'^u/(?P<username>' + settings.RSTR_USERNAME + r')/$',
        views.profile_view, name="profile_page"),

    # Let auth user set a flag on view user (like, nope, block, etc).
    url(r'^flag/(?P<action>set|delete)/'
        r'(?P<flag>[a-zA-Z0-9_-]{2,30})/'
        r'(?P<username>' + settings.RSTR_USERNAME + r')/$',
        views_me.me_flag_view, name="me_flag_page"),

    url(r'^mod/deluser/(?P<pk>\d*)/$', views_mod.mod_deluser_view,
        name="mod_deluser_page"),
    url(r'^mod/reports/$', views_mod.mod_report_view,
        name="mod_report_page"),
    url(r'^mod/reports/(?P<pk>\d*)/$', views_mod.mod_report_view,
        name="mod_report_item_page"),

    url(r'^stats/$', views.stats_view, name="stats"),

    url(r'^map/$', views.usermap_view, name="usermap"),

    # API URLs

    url(r'^api/v1/filter-members.json$', views_api.filter_members_view,
        name="filter_members"),
]

api_urlpatterns = [

    # POST here to store user selected search options and generate cached
    # search results. Then request the first page with the below results view.
    url(r'^api/v1/search$',
        views_api.search_params, name="search_params_api"),
    # Search results as paginated list view of user profiles
    url(r'^api/v1/results$',
        views_api.results_list, name="results_list_api"),

    # Show "view user"'s profile page.
    url(r'^api/v1/u/(?P<username>' + settings.RSTR_USERNAME + r')$',
        views_api.user_detail, name="api_user_detail"),

    # Auth user, and auth user picture upload
    url(r'^api/v1/authuser$',
        views_api.authuser_detail, name='authuser_detail_api'),
    url(r'^api/v1/authuser-picture$',
        views_api.authuser_picture, name='authuser_picture_api'),

    # Private messages between auth user and another user.
    url(r'^api/v1/pms/(?P<username>' + settings.RSTR_USERNAME + r')$',
        views_api.pms_list, name='pms_list_api'),

    # Show all users that subscribe to a specific subreddit.
    url(r'^api/v1/r/(?P<sr>' + settings.RSTR_SR_NAME + r')$',
        views_api.sr_user_list, name="sr_user_list_api"),

    url(r'^api/v1/upvotes_recv$',
        views_api.upvotes_recv_api, name="upvotes_recv_api"),
    url(r'^api/v1/matches$',
        views_api.matches_api, name="matches_api"),
    url(r'^api/v1/upvotes_sent',
        views_api.upvotes_sent_api, name="upvotes_sent_api"),
    url(r'^api/v1/downvotes_sent',
        views_api.downvotes_sent_api, name="downvotes_sent_api"),

    url(r'^api/v1/visits',
        views_api.visits_api, name="visits_api"),
    url(r'^api/v1/visitors',
        views_api.visitors_api, name="visitors_api"),

    url(r'^api/v1/pushnotifications',
        views_api.push_notification_api, name="push_notification_api"),

    # Let auth user set a flag on view user.
    url(r'^api/v1/flag/(?P<flag>(like|nope))/'
        r'(?P<username>' + settings.RSTR_USERNAME + r')$',
        views_api.flag_api, name="flag_api"),


]

api_urlpatterns = format_suffix_patterns(api_urlpatterns)

urlpatterns += api_urlpatterns

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()

    urlpatterns += static('/app/', document_root=
                          '/home/chris/dev/new/reddmeet-material/dist/')
    urlpatterns += static('/node_modules/', document_root=
                          '/home/chris/dev/new/reddmeet-material/node_modules/')
    urlpatterns += static('/s/', document_root=
                          path.join(settings.BASE_DIR, 'avatars/s/'))
    urlpatterns += static('/m/', document_root=
                          path.join(settings.BASE_DIR, 'avatars/m/'))
