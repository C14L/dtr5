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
from django.conf.urls import include, url
from django.contrib import admin
from simple_reddit_oauth import urls as simple_reddit_oauth_urls
from dtr5app import views

R_USERNAME = r'(?P<username>[a-zA-Z0-9_-]{2,30})'

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^account/', include(simple_reddit_oauth_urls)),
    url(r'^$', views.home_view, name="home_page"),

    # Users preferences page, and URIs to POST to.
    url(r'^me/$', views.me_view, name="me_page"),
    url(r'^me/update/$', views.me_update_view, name="me_update_page"),
    url(r'^me/locate/$', views.me_locate_view, name="me_locate_page"),
    url(r'^me/favsr/$', views.me_favsr_view, name="me_favsr_page"),
    url(r'^me/manual/$', views.me_manual_view, name="me_manual_page"),
    url(r'^me/pic/$', views.me_picture_view, name="me_picture_page"),
    url(r'^me/pic/delete$', views.me_pic_del_view, name="me_pic_del_page"),
    url(r'^me/flag/delete$', views.me_flag_del_view, name="me_flag_del_page"),
    url(r'^me/likes$', views.me_like_view, name="me_like_page"),
    url(r'^me/nopes$', views.me_nope_view, name="me_nope_page"),
    url(r'^me/account/delete$', views.me_account_del_view,
        name="me_account_del_page"),

    url(r'^search/$', views.me_search_view, name="me_search_page"),
    # Show a list of matches (auth user and view user mutual likes).
    url(r'^matches/$', views.matches_view, name="matches_page"),
    # Show all users that subscribe to a specific subreddit.
    # --> TODO: Maybe not really needed?
    url(r'^r/(?P<sr>[a-zA-Z0-9_-]{2,30})/$', views.sr_view, name="sr_page"),
    # Show "view user"'s profile page.
    url(r'^u/' + R_USERNAME + r'/$', views.profile_view, name="profile_page"),
    # Let auth user set a flag on view user (like, nope, block, etc).
    url(r'^flag/(?P<action>set|delete)/(?P<flag>[a-zA-Z0-9_-]{2,30})/' +
        R_USERNAME + r'/$', views.me_flag_view, name="me_flag_page"),

    url(r'^mod/deluser/(?P<pk>\d*)/$', views.mod_deluser_view,
        name="mod_deluser_page"),
    url(r'^mod/reports/$', views.mod_report_view,
        name="mod_report_page"),
    url(r'^mod/reports/(?P<pk>\d*)/$', views.mod_report_view,
        name="mod_report_item_page"),
]
