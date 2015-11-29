from django.contrib import admin
from .models import Profile, Flag, Sr, Subscribed, Report


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('_user_id', '__str__', 'name', 'created', 'accessed',
                    'link_karma', 'comment_karma', 'sex', 'over_18', )


class SrAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name',
                    'subscribers', 'subscribers_here')


class SubscribedAdmin(admin.ModelAdmin):
    list_display = ('user', 'sr', )


class FlagAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'flag', 'created', )


class ReportAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'created', 'resolved', 'reason', )


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Sr, SrAdmin)
admin.site.register(Subscribed, SubscribedAdmin)
admin.site.register(Flag, FlagAdmin)
admin.site.register(Report, ReportAdmin)
