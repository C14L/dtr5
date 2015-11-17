from django.contrib import admin
from .models import Profile, Flag, Sr, Subscribed


class ProfileAdmin(admin.ModelAdmin):
    pass


class SrAdmin(admin.ModelAdmin):
    pass


class SubscribedAdmin(admin.ModelAdmin):
    pass


class FlagAdmin(admin.ModelAdmin):
    pass


admin.site.register(Profile, ProfileAdmin)
admin.site.register(Sr, SrAdmin)
admin.site.register(Subscribed, SubscribedAdmin)
admin.site.register(Flag, FlagAdmin)
