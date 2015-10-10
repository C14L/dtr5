import logging
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


class Profile(models.Model):
    """All user specific information."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                primary_key=True, related_name="profile")
    # static Reddit user account data:
    name = models.CharField(default="", max_length=20)
    created = models.DateField(null=True, default=None)  # created_utc
    updated = models.DateTimeField(null=True, default=None)
    # changeable Reddit user account data:
    link_karma = models.IntegerField(default=0)
    comment_karma = models.IntegerField(default=0)
    over_18 = models.BooleanField(default=False)
    hide_from_robots = models.BooleanField(default=False)
    has_verified_email = models.BooleanField(default=False)
    # other data:
    lat = models.FloatField(null=True, default=None)
    lng = models.FloatField(null=True, default=None)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

        index_together = [["lat", "lng"], ]

    def __str__(self):
        return self.name


class Sr(models.Model):
    """List of sr names each user is subscribed to."""
    id = models.CharField(primary_key=True, max_length=10)  # sans "t5_"
    name = models.CharField(max_length=50, editable=False)
    created = models.DateField(null=True, default=None)  # created_utc
    url = models.CharField(default="", max_length=50, unique=True)  # "/r/de"
    over18 = models.BooleanField(default=False)
    lang = models.CharField(default="", max_length=10)
    title = models.CharField(default="", max_length=100)
    header_title = models.CharField(default="", max_length=100)
    display_name = models.CharField(default="", max_length=100)
    # public or private
    subreddit_type = models.CharField(default="", max_length=50)
    # Subreddit subscribers
    subscribers = models.IntegerField(default=0)
    # Subreddir subscribers with an account here on this site
    subscribers_here = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Subreddit"
        verbose_name_plural = "Subreddits"
        ordering = ['display_name']

    def __str__(self):
        return self.name


class Subscribed(models.Model):
    user = models.ForeignKey(User, editable=False, related_name="subs")
    sr = models.ForeignKey(Sr, editable=False, related_name="users")
    user_is_contributor = models.BooleanField(default=False)
    user_is_moderator = models.BooleanField(default=False)
    user_is_subscriber = models.BooleanField(default=True)
    user_is_banned = models.BooleanField(default=False)
    user_is_muted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Subreddit subscription"
        verbose_name_plural = "Subreddit subscriptions"

    def __str__(self):
        return '{} --> {}'.format(self.user.username, self.sr.name)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    logger.info('User -> post_save signal received.')
    if created:
        logger.info('New user instance was created.')
        profile = Profile(user=instance)
        profile.name = instance.username
        try:
            profile.save()
        except:
            logger.error('Profile "%s" not created', instance.username)
            pass
