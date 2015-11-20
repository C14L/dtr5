import json
import logging
from datetime import date
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
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
    # JSON string with a list of pictures.
    # url: char field with the complete picture URL.
    # src: char field with the comeplete URL to the pic's source page.
    pics_str = models.TextField(default='')

    # even more manually input data
    tagline = models.CharField(default='', max_length=160)          # unused
    height = models.PositiveSmallIntegerField(default=0)  # in cm   # unused
    weight = models.PositiveSmallIntegerField(default=0)  # in kg   # unused
    lookingfor = models.PositiveSmallIntegerField(                  # unused
        blank=True, null=True, default=None, choices=settings.LOOKINGFOR)
    relstatus = models.PositiveSmallIntegerField(                   # unused
        blank=True, null=True, default=None, choices=settings.RELSTATUS)
    education = models.PositiveSmallIntegerField(                   # unused
        blank=True, null=True, default=None, choices=settings.EDUCATION)
    fitness = models.PositiveSmallIntegerField(                     # unused
        blank=True, null=True, default=None, choices=settings.FITNESS)

    # Some numbers
    views_count = models.PositiveSmallIntegerField(default=0)
    matches_count = models.PositiveSmallIntegerField(default=0)
    like_sent_count = models.PositiveSmallIntegerField(default=0)   # unused
    like_recv_count = models.PositiveSmallIntegerField(default=0)   # unused
    nope_sent_count = models.PositiveSmallIntegerField(default=0)   # unused
    nope_recv_count = models.PositiveSmallIntegerField(default=0)   # unused
    block_sent_count = models.PositiveSmallIntegerField(default=0)  # unused
    block_recv_count = models.PositiveSmallIntegerField(default=0)  # unused

    # f_ --> user search settings: who shows up in search results?
    f_sex = models.PositiveSmallIntegerField(default=0)
    f_distance = models.PositiveSmallIntegerField(default=0)  # km, max 32767
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
    pics = []  # helper list, this will be serialized on save.

    class Meta:
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"
        index_together = [["lat", "lng"], ]

    def __str__(self):
        return self.name

    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)
        # Unserialilze pictures JSON string into list.
        try:
            self.pics = json.loads(self.pics_str)
        except ValueError:
            self.pics = []

    def save(self, *args, **kwargs):
        # Don't store more than 10 pictures per profile.
        if len(self.pics) > 10:
            self.pics = self.pics[:10]
        # For all pictures, make sure to use the right imgur size.
        for pic in self.pics:
            if '//i.imgur.com/' in pic['url']:
                pic['src'] = get_imgur_page_from_picture_url(pic['url'])
                # do the same for other common image hosters... who?
                # -- TODO --
        # Serialilze pics list into JSON string.
        self.pics_str = json.dumps(self.pics, ensure_ascii=False)
        super(Profile, self).save(*args, **kwargs)

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

    def set_subscribed_subs(self):
        if not hasattr(self, 'subscribed_subs'):
            qs = self.user.subs.all().prefetch_related('sr')
            self.subscribed_subs = list(qs)

    def set_common_subs(self, subs_list):
        """
        sets the common_subs and not_common_subs properties on the instance.
        lists of all subs the instance user is (not) subscribed to and that
        also appear in the subs_list list. the subs_list list is usually a
        QuerySet of auth user's subs.
        """
        self.common_subs = []
        self.not_common_subs = []
        self.set_subscribed_subs()
        subs_list_pks = [x.sr.pk for x in subs_list]
        for x in self.subscribed_subs:
            if x.sr.pk in subs_list_pks:
                self.common_subs.append(x)
            else:
                self.not_common_subs.append(x)

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

    def match_with(self, view_user):
        """Return True if user is a match (multual like) with view_user."""
        return (Flag.objects.filter(flag=Flag.LIKE_FLAG).filter(
            Q(sender=self.user, receiver=view_user) |
            Q(receiver=self.user, sender=view_user)).count() == 2)

    def does_like(self, view_user):
        return (Flag.objects.filter(flag=Flag.LIKE_FLAG, sender=self.user,
                                    receiver=view_user).exists())

    def does_nope(self, view_user):
        return (Flag.objects.filter(flag=Flag.NOPE_FLAG, sender=self.user,
                                    receiver=view_user).exists())

    def reset_all(self):
        # TODO: find generic method to do this, using each field's default.
        self.created = None
        self.updated = None
        self.link_karma = 0
        self.comment_karma = 0
        self.over_18 = False
        self.hide_from_robots = True
        self.has_verified_email = False
        self.gold_creddits = False
        self.lat = 0.0
        self.lng = 0.0
        self.dob = None
        self.sex = 0
        self.about = ''
        self.pics_str = ''
        self.views_count = 0
        self.matches_count = 0
        self.like_sent_count = 0
        self.like_recv_count = 0
        self.nope_sent_count = 0
        self.nope_recv_count = 0
        self.block_sent_count = 0
        self.block_recv_count = 0
        self.f_sex = 0
        self.f_distance = 0
        self.f_minage = 18
        self.f_maxage = 100
        self.f_over_18 = True
        self.f_has_verified_email = False
        self.x_match_search_options = False
        self.x_only_no_over_18 = False
        self.x_has_verified_email = False
        self.x_min_account_age_days = 2
        self.x_min_comment_karma = 50
        self.x_min_link_karma = 0


class Flag(models.Model):
    """Store relations between users, such as 'like', 'block', etc."""
    LIKE_FLAG = 1
    NOPE_FLAG = 2
    BLOCK_FLAG = 3
    REPORT_FLAG = 4
    FLAG_CHOICES = ((LIKE_FLAG, 'like'), (NOPE_FLAG, 'nope'),
                    (BLOCK_FLAG, 'block'), (REPORT_FLAG, 'report'), )
    FLAG_DICT = {x[1]: x[0] for x in FLAG_CHOICES}

    sender = models.ForeignKey(User, related_name="flags_sent")
    receiver = models.ForeignKey(User, related_name="flags_received")
    flag = models.PositiveSmallIntegerField(blank=False, choices=FLAG_CHOICES)
    created = models.DateTimeField(default=now)

    class Meta:
        verbose_name = 'user flag'
        verbose_name_plural = 'user flags'
        unique_together = ['sender', 'receiver', 'flag']

    def __str__(self):
        return '{} --{}--> {}'.format(self.sender.username,
                                      self.get_flag_display(),
                                      self.receiver.username)

    @classmethod
    def delete_flag(cls, sender, receiver):
        """
        All flag relations are unique, so that there is only ever one flag set
        between a pair of users. Deleting a flag between two users always
        deletes all flags between them.
        """
        for x in cls.objects.filter(sender=sender, receiver=receiver):
            x.delete()

    @classmethod
    def set_flag(cls, sender, receiver, flag):
        """
        All current flags are "unique", so that setting one of them
        on a user, automatically removes all previously set flags on
        that user.
        """
        cls.delete_flag(sender, receiver)
        return cls.objects.create(sender=sender, receiver=receiver,
                                  flag=cls.FLAG_DICT[flag])


class Report(models.Model):
    """Reason and details of user profile reports."""
    REASON_CHOICES = getattr(settings, 'REPORT_REASON_CHOICES', (
        (1, 'spam'), (2, 'personal information'), (3, 'inapropriate picture'),
        (4, 'sexualizing minors'), (5, 'other (write below)')))

    sender = models.ForeignKey(User, related_name="reports_sent")
    receiver = models.ForeignKey(User, related_name="reports_received")
    created = models.DateTimeField(default=now)
    resolved = models.DateTimeField(default=None, null=True, blank=True)
    reason = models.PositiveSmallIntegerField(choices=REASON_CHOICES)
    details = models.TextField(default='')

    class Meta:
        verbose_name = 'user report'
        verbose_name_plural = 'user reports'
        index_together = [['sender', 'receiver'],
                          ['reason', 'receiver'], ]

    def __str__(self):
        return '{} reported for {}'.format(self.receiver.username,
                                           self.get_reason_display())


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
    # public, restricted, or private
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
        return '{} ({}/{})'.format(self.name,
                                   self.subscribers_here, self.subscribers)


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
