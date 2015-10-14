import logging
from datetime import date
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from toolbox import (get_imgur_page_from_picture_url,
                     get_western_zodiac,
                     get_western_zodiac_symbol,
                     get_eastern_zodiac,
                     get_eastern_zodiac_symbol,
                     distance_between_geolocations)

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
    # set if the reddit account or any subbed sr is "over_18"
    over_18 = models.BooleanField(default=False)
    hide_from_robots = models.BooleanField(default=False)
    has_verified_email = models.BooleanField(default=False)
    gold_creddits = models.BooleanField(default=False)

    # other data:
    lat = models.FloatField(default=0.0)
    lng = models.FloatField(default=0.0)

    # manually input data
    dob = models.DateField(null=True, default=None)  # user's b'day
    sex = models.IntegerField(default=0, choices=settings.SEX)
    about = models.TextField(default='')

    # f_ --> user search settings: who shows up in search results?
    f_sex = models.PositiveSmallIntegerField(default=0)
    f_distance = models.PositiveSmallIntegerField(default=0)  # max 32767
    f_minage = models.PositiveSmallIntegerField(default=18)
    f_maxage = models.PositiveSmallIntegerField(default=100)
    # find users with the over_18 profile value set to True or who
    # are subscribed to any "over_18" subreddits?
    f_over_18 = models.BooleanField(default=True)
    # find only users that have a verified email on reddit?
    f_has_verified_email = models.BooleanField(default=False)

    # x_ --> only show my profile listed in another redditor's
    # search results, if the other redditor...
    # ...matches all my above search (f_*) options.
    x_match_search_options = models.BooleanField(default=False)
    # ...is not subbed to any over_18 subreddits and their reddit
    # account is not set to "over_18" either.
    x_only_no_over_18 = models.BooleanField(default=False)
    # ...has a verified email address on reddit.
    x_has_verified_email = models.BooleanField(default=False)
    # ...has an account that is at least so many days old.
    # (do not use models.DurationField, the resolution is too high,
    # its less compatible, and the functionality isn't needed here)
    x_min_account_age_days = models.PositiveSmallIntegerField(default=2)
    # ...has at least so much comment karma.
    x_min_comment_karma = models.PositiveIntegerField(default=50)
    # ...has at least so much link karma.
    x_min_link_karma = models.PositiveIntegerField(default=0)

    # Can be set for distance calculation.
    viewer_lat = None
    viewer_lng = None
    common_subs = []

    class Meta:
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"
        index_together = [["lat", "lng"], ]

    def __str__(self):
        return self.name

    def get_sex_symbol(self):
        """Returns the symbol for the user's sex."""
        try:
            return [x[1] for x in settings.SEX_SYMBOL if x[0] == self.sex][0]
        except IndexError:
            return ''

    def get_western_zodiac_display(self):
        return get_western_zodiac(self.dob)

    def get_western_zodiac_symbol(self):
        return get_western_zodiac_symbol(self.dob)

    def get_eastern_zodiac_display(self):
        return get_eastern_zodiac(self.dob)

    def get_eastern_zodiac_symbol(self):
        return get_eastern_zodiac_symbol(self.dob)

    def get_age(self):
        try:
            delta = date.today() - self.dob
            return int(delta.days / 365)
        except:
            return ''

    def set_common_subs(self, subs_all):
        """  ...  """
        self.common_subs = []
        li = list(self.user.subs.all())
        for s1 in subs_all:
            for s2 in li:
                if s1.sr.pk == s2.sr.pk:
                    self.common_subs.append(s2)
                    break

    def set_viewer_latlng(self, vlat, vlng):
        self.viewer_lat = vlat
        self.viewer_lng = vlng

    def get_distance(self):
        """Return distance in meters between lat/lng and instance's loc."""
        try:
            return int(distance_between_geolocations(
                (self.lat, self.lng), (self.viewer_lat, self.viewer_lng)))
        except TypeError:
            return 99999999

    def get_distance_in_km(self):
        """Returns distance in km between lat/lng and instance's location"""
        return float(self.get_distance() / 1000)

    def get_distance_in_miles(self):
        return float(self.get_distance_in_km() * 0.621371)


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
        verbose_name = "subreddit"
        verbose_name_plural = "subreddits"
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
    is_favorite = models.BooleanField(default=False)  # user fav'd this sr.

    class Meta:
        verbose_name = "subreddit subscription"
        verbose_name_plural = "subreddit subscriptions"
        ordering = ['sr__display_name']

    def __str__(self):
        return '{} --> {}'.format(self.user.username, self.sr.name)


class Picture(models.Model):
    user = models.ForeignKey(User, editable=False, related_name="pics")
    url = models.CharField(max_length=150)
    src = models.CharField(default='', max_length=150)  # source page URL.

    class Meta:
        verbose_name = "picture"
        verbose_name_plural = "pictures"
        unique_together = (('user', 'url'), )

    def __init__(self, *args, **kwargs):
        super(Picture, self).__init__(*args, **kwargs)

    def __str__(self):
        return '{} --> {}'.format(self.user.username, self.url)

    def save(self, *args, **kwargs):
        if '//i.imgur.com/' in self.url:
            # if this is a imgur URL, get a link to the source page.
            self.src = get_imgur_page_from_picture_url(self.url)
            # do the same for other common image hosters... who?
            # -- TODO --
        super(Picture, self).save(*args, **kwargs)


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
