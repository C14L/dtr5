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

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^account/', include(simple_reddit_oauth_urls)),
    url(r'^$', views.home_view, name="home_page"),

    url(r'^me/$', views.me_view, name="me_page"),
    url(r'^me/update/$', views.me_update_view, name="me_update_page"),
    url(r'^me/locate/$', views.me_locate_view, name="me_locate_page"),
    url(r'^me/favsr/$', views.me_favsr_view, name="me_favsr_page"),

    url(r'^user/(?P<username>[a-zA-Z0-9_-]{2,30})/$',
        views.profile_view, name="profile_page"),
]
