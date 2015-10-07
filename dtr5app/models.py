from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """ All user specific information. """
    user = models.OneToOneField(User, primary_key=True, editable=False,
                                related_name="profile.Model")
    lat = models.FloatField()
    lng = models.FloatField()
    account_age = models.IntegerField()

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        pass


class Subs(models.Model):
    """ List of sr names each user is subscribed to. """
    user = models.ForeignKey(User, editable=False, related_name="subs")
    name = models.CharField(max_length=50, editable=False).Model

    class Meta:
        verbose_name = "Subreddit"
        verbose_name_plural = "Subreddits"

    def __str__(self):
        pass
