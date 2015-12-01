import json
import logging
from datetime import date
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.fields import NOT_PROVIDED
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from toolbox import (get_imgur_page_from_picture_url,
                     get_western_zodiac,
                     get_western_zodiac_symbol,
                     get_eastern_zodiac,
                     get_eastern_zodiac_symbol,
                     distance_between_geolocations,
                     get_age,
                     sr_str_to_list)

logger = logging.getLogger(__name__)


class Profile(models.Model):
    """All user specific information."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                primary_key=True, related_name="profile")
    # static Reddit user account data:
    name = models.CharField(default="", max_length=20)
    created = models.DateField(null=True, default=None)  # created_utc
    updated = models.DateTimeField(null=True, default=None)
    accessed = models.DateTimeField(null=True, default=None)  # last activity

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
    _pics = models.TextField(default='')

    # even more manually input data
    tagline = models.CharField(default='', max_length=160)          # unused
    height = models.PositiveSmallIntegerField(default=0)  # in cm   # unused
    weight = models.PositiveSmallIntegerField(default=0)  # in kg   # unused
    _lookingfor = models.CommaSeparatedIntegerField(  # settings.LOOKINGFOR
        max_length=50, blank=True, default='')
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
    f_over_18 = models.BooleanField(default=True)                   # unused
    # find only users that have a verified email on reddit?
    f_has_verified_email = models.BooleanField(default=False)       # unused

    # space separated list of subreddit names to ignore in search
    _f_ignore_sr_li = models.CharField(default='', max_length=250)
    # subreddits with more members than this are ignored in search
    f_ignore_sr_max = models.PositiveIntegerField(default=100000000)
    # space separated list of subreddits whose subscribers will be
    # REMOVED from user's search results.
    _f_exclude_sr_li = models.CharField(default='', max_length=250)

    # x_ --> only show my profile listed in another redditor's
    # search results, if the other redditor...

    # ...matches all my above search (f_*) options.
    x_match_search_options = models.BooleanField(default=False)     # unused
    # ...is not subbed to any over_18 subreddits and their reddit
    # account is not set to "over_18" either.
    x_only_no_over_18 = models.BooleanField(default=False)          # unused
    # ...has a verified email address on reddit.
    x_has_verified_email = models.BooleanField(default=False)       # unused
    # ...has an account that is at least so many days old.
    # (do not use models.DurationField, the resolution is too high,
    # its less compatible, and the functionality isn't needed here)
    x_min_account_age_days = models.PositiveSmallIntegerField(default=2)
    # ...has at least so much comment karma.                        # unused
    x_min_comment_karma = models.PositiveIntegerField(default=50)   # unused
    # ...has at least so much link karma.
    x_min_link_karma = models.PositiveIntegerField(default=0)       # unused

    # let the user chose if they want to see distances in km or miles.
    _pref_distance_unit = models.CharField(null=True, default=None,
                                           max_length=2)

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
        return self.user.username

    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(Profile, self).save(*args, **kwargs)

    def _user_id(self):
        return self.user.id

    @property
    def f_ignore_sr_li(self):
        return sr_str_to_list(self._f_ignore_sr_li)

    @f_ignore_sr_li.setter
    def f_ignore_sr_li(self, li):
        if isinstance(li, str):
            li = sr_str_to_list(li)  # if it a string of subreddits, clean it.
        self._f_ignore_sr_li = ' '.join(li)

    @property
    def f_exclude_sr_li(self):
        return sr_str_to_list(self._f_exclude_sr_li)

    @f_exclude_sr_li.setter
    def f_exclude_sr_li(self, li):
        if isinstance(li, str):
            li = sr_str_to_list(li)  # if it a string of subreddits, clean it.
        self._f_exclude_sr_li = ' '.join(li)

    @property
    def pics(self):
        try:
            return json.loads(self._pics)
        except ValueError:
            return []

    @pics.setter
    def pics(self, li):
        if not isinstance(li, list):
            raise ValueError('list expected')
        # Don't store more than 10 pictures per profile.
        li = li[:settings.USER_MAX_PICS_COUNT]
        # For all pictures, make sure to use the right imgur size.
        for pic in li:
            if '//i.imgur.com/' in pic['url']:
                pic['src'] = get_imgur_page_from_picture_url(pic['url'])
                # do the same for other common image hosters... who?
                # -- TODO --
        # Serialilze pics list into JSON string.
        self._pics = json.dumps(li, ensure_ascii=False)

    @property
    def lookingfor(self):
        if self._lookingfor:
            return [int(x) for x in self._lookingfor.split(',')]
        else:
            return []

    @lookingfor.setter
    def lookingfor(self, li):
        if isinstance(li, list):
            self._lookingfor = ','.join([str(x) for x in li])
        else:
            raise ValueError('list expected')

    @property
    def pref_distance_unit(self):
        return self._pref_distance_unit

    @pref_distance_unit.setter
    def pref_distance_unit(self, val):
        if val in ['km', 'mi']:
            self._pref_distance_unit = val
        else:
            raise ValueError('pref_distance_unit must be "km" or "mi".')

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
            return get_age(self.dob)
        except:
            return ''

    def set_subscribed_subs(self):
        """make sure to fetch and cache all subs the user is subscribed to"""
        if not hasattr(self, 'subscribed_subs'):
            qs = self.user.subs.all().prefetch_related('sr')
            self.subscribed_subs = list(qs)

    def set_common_subs(self, subs_list, f_ignore_sr_li, f_ignore_sr_max):
        """
        sets the common_subs and not_common_subs properties on the instance.
        lists of all subs the instance user is (not) subscribed to and that
        also appear in the subs_list list. the subs_list list is usually a
        QuerySet of auth user's subs.

        update: respect authuser's "f_ignore_sr_li" and "f_ignore_sr_max"
        search values: subs that don't match these search settings must
        be excluded from the common subs.

        :subs_list: list of auth user's subscribed subreddits.
        :f_ignore_sr_max: auth user set this limit to exclude larger subs.
        :f_ignore_sr_li: auth user's list of subreddit names to ignore.
        """
        self.common_subs = []  # collect here the common subs
        self.not_common_subs = []   # and here all the other

        # make sure "self.subscribed_subs" contains all subs of view_user.
        self.set_subscribed_subs()

        # prefetch all related subreddits, for the below loop
        subs_list = subs_list.prefetch_related('sr')

        # fill the list with only the primary keys of all subs.
        subs_list_pks = []
        for sub in subs_list:
            # either max val.must not be set, or it must be lower than subs-nr.
            c1 = (not f_ignore_sr_max or sub.sr.subscribers < f_ignore_sr_max)
            # the sub name should not be in the ignore list.
            c2 = (sub.sr.display_name not in f_ignore_sr_li)

            if c1 and c2:
                # if there is a max value, the sub must have LESS subscribers.
                subs_list_pks.append(sub.sr.pk)

        # now look at all of view_user's subs and spit them between those that
        # exist in auth user's "subs_list_pks" and those that don't.
        for sub in self.subscribed_subs:
            if sub.sr.pk in subs_list_pks:
                self.common_subs.append(sub)
            else:
                self.not_common_subs.append(sub)

    def set_viewer_latlng(self, vlat, vlng):
        """Retuired to set view_user lat/lng before calling get_distance()."""
        self.viewer_lat = vlat
        self.viewer_lng = vlng

    def get_distance(self):
        """
        Return distance in meters between instance location and viewer_lat/lng
        as set by a previous call of set_viewer_latlng().
        """
        try:
            return int(distance_between_geolocations(
                (self.lat, self.lng), (self.viewer_lat, self.viewer_lng)))
        except TypeError:
            return 99999999

    def get_distance_in_km(self):
        """Returns above distance in km."""
        return float(self.get_distance() / 1000)

    def get_distance_in_miles(self):
        """Returns above distance in miles."""
        return float(self.get_distance_in_km() * 0.621371)

    def match_with(self, view_user):
        """Return True if user is a match (multual like) with view_user."""
        return (Flag.objects.filter(flag=Flag.LIKE_FLAG).filter(
            Q(sender=self.user, receiver=view_user) |
            Q(receiver=self.user, sender=view_user)).count() == 2)

    def does_like(self, view_user):
        """Return True is the instance user "liked" view_user."""
        return (Flag.objects.filter(flag=Flag.LIKE_FLAG, sender=self.user,
                                    receiver=view_user).exists())

    def does_nope(self, view_user):
        """Return True is the instance user "noped" view_user."""
        return (Flag.objects.filter(flag=Flag.NOPE_FLAG, sender=self.user,
                                    receiver=view_user).exists())

    def reset_all_and_save(self):
        """
        Resets to default values all data field of a user profile. Used when
        a user deletes their account.
        """
        for x in self._meta.fields:
            if x.default != NOT_PROVIDED:
                setattr(self, x.name, x.default)
        self.pics = []
        self.save()


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
    display_name = models.CharField(default="", max_length=100, db_index=True)
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
