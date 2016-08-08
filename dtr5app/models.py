import json

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.fields import NOT_PROVIDED
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

# from bitfield import BitField

from toolbox import (
                     distance_between_geolocations,
                     get_age,
                     get_eastern_zodiac,
                     get_eastern_zodiac_symbol,
                     get_imgur_page_from_picture_url,
                     get_western_zodiac,
                     get_western_zodiac_symbol,
                     set_imgur_url,
                     sr_str_to_list,
                    )


class Profile(models.Model):
    """All user specific information."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                primary_key=True, editable=False,
                                related_name="profile")
    # static Reddit user account data:
    name = models.CharField(default="", max_length=20)
    created = models.DateField(null=True, default=None)  # REDDIT accunt created
    updated = models.DateTimeField(null=True, default=None)  # profile updated
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
    fuzzy = models.IntegerField(default=2)  # km lat/lng fuzziness radius

    # manually input data
    dob = models.DateField(null=True, default=None)  # user's b'day
    sex = models.IntegerField(default=0, choices=settings.SEX)
    about = models.TextField(default='')
    # JSON string with a list of pictures.
    # url: char field with the complete picture URL.
    # src: char field with the comeplete URL to the pic's source page.
    _pics = models.TextField(default='')
    background_pic = models.CharField(default='', max_length=250)

    # classify as only or mostly dating or friends, or both.
    herefor = models.PositiveIntegerField(
        choices=settings.HEREFOR, default=settings.HEREFOR_FRIENDS_OR_DATING)
    # The user may want to either exclude people who are here /only/ for dating
    # or /only/ for friends. HEREFOR_ONLY_FRIENDS / HEREFOR_ONLY_DATING
    herefor_exclude = models.PositiveSmallIntegerField(default=0)

    # even more manually input data
    tagline = models.CharField(default='', max_length=160)          # unused
    height = models.PositiveSmallIntegerField(default=0)  # in cm   # unused
    weight = models.PositiveSmallIntegerField(default=0)  # in kg   # unused
    _lookingfor = models.CommaSeparatedIntegerField(  # settings.LOOKINGFOR
        max_length=50, blank=True, default='')
    relstatus = models.PositiveSmallIntegerField(default=1,
                                                 choices=settings.RELSTATUS)
    education = models.PositiveSmallIntegerField(default=1,  # unused
                                                 choices=settings.EDUCATION)
    fitness = models.PositiveSmallIntegerField(default=1,  # unused
                                               choices=settings.FITNESS)

    # Some numbers
    views_count = models.PositiveSmallIntegerField(default=0)
    matches_count = models.PositiveSmallIntegerField(default=0)

    # All "new_*_count" values are set to 0 every time they are displayed,
    # like its done on Reddit with "new messages".
    new_matches_count = models.PositiveSmallIntegerField(default=0)
    new_likes_count = models.PositiveSmallIntegerField(default=0)
    new_views_count = models.PositiveSmallIntegerField(default=0)

    # Send notification when upvote received via Reddit PM.
    upvote_notif_now = models.BooleanField(default=False)  # for every upvote
    upvote_notif_weekly = models.BooleanField(default=True)  # digest once week

    # more counters, currently unused.
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
    f_over_18 = models.BooleanField(default=True)  # --> unused
    # find only users that have a verified email on reddit?
    f_has_verified_email = models.BooleanField(default=False)
    # find only stable user accounts with a certain age and karma.
    f_is_stable = models.BooleanField(default=False)

    # space separated list of subreddit names to ignore in search
    # --- DEPRECATED ---
    _f_ignore_sr_li = models.CharField(default='', max_length=800)
    # subreddits with more members than this are ignored in search
    # --- DEPRECATED ---
    f_ignore_sr_max = models.PositiveIntegerField(default=100000000)
    # space separated list of subreddits whose subscribers will be
    # REMOVED from user's search results.
    # --- DEPRECATED ---
    _f_exclude_sr_li = models.CharField(default='', max_length=800)
    # hide profiles without picture in search results?
    f_hide_no_pic = models.BooleanField(default=False)

    # x_ --> only show my profile listed in another redditor's
    # search results, if the other redditor...
    # -- CURRENTLY UNUSED --

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
        # --- DEPRECATED ---
        return sr_str_to_list(self._f_ignore_sr_li)

    @f_ignore_sr_li.setter
    def f_ignore_sr_li(self, li):
        # --- DEPRECATED ---
        if isinstance(li, str):
            li = sr_str_to_list(li)  # if it a string of subreddits, clean it.
        self._f_ignore_sr_li = ' '.join(li)

    @property
    def f_exclude_sr_li(self):
        # --- DEPRECATED ---
        return sr_str_to_list(self._f_exclude_sr_li)

    @f_exclude_sr_li.setter
    def f_exclude_sr_li(self, li):
        # --- DEPRECATED ---
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

    @property
    def western_zodiac(self):
        return get_western_zodiac(self.dob)

    @property
    def western_zodiac_symbol(self):
        return get_western_zodiac_symbol(self.dob)

    @property
    def eastern_zodiac(self):
        return eastern_zodiac(self.dob)

    @property
    def eastern_zodiac_symbol(self):
        return get_eastern_zodiac_symbol(self.dob)

    def display_background_pic(self):
        """
        Return the URL of the background_pic with the correct size Byte in
        case of Imgur pictures.
        """
        return set_imgur_url(self.background_pic, size='l')

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

    @property
    def age(self):
        return get_age(self.dob)

    @property
    def subscribed_subs(self):
        """
        Return (and cache) all subs this instance's user is subscribed to.
        """
        if not hasattr(self, '_subscribed_subs'):
            self._subscribed_subs = \
                list(self.user.subs.all().prefetch_related('sr'))

        return self._subscribed_subs

    def _set_common_not_common_subs(self, user, fav_only=True):
        """
        Prepares two cached lists: "common_subs" and "not_common_subs" that
        hold the common and not common subs betweeen the instance user and
        those in the subs_list list. The subs_list list is a QuerySet
        of auth user's subs.

        :subs_list: QS or list of auth user's subreddit subscriptions.
        :fav_only: only consider objects in subs_list where is_favorite=True.
        """
        if settings.DEBUG:
            print('_set_common_not_common_subs() called...')
        self._common_subs = []
        self._not_common_subs = []

        subs_list = user.subs.all()
        if fav_only:
            subs_list = subs_list.filter(is_favorite=True)

        # fill the list with only the primary keys of all subs.
        subs_list_pks = subs_list.values_list('sr', flat=True)

        # now look at all of view_user's subs and spit them between those that
        # exist in auth user's "subs_list_pks" and those that don't.
        for sub in self.subscribed_subs:
            if sub.sr.pk in subs_list_pks:
                if settings.DEBUG:
                    print('YES!', sub.sr.display_name)
                self._common_subs.append(sub)
            else:
                if settings.DEBUG:
                    print('NOO', sub.sr.display_name)
                self._not_common_subs.append(sub)

    def get_common_subs(self, user, fav_only=True):
        """
        Return a list with the "common_subs" the instance user is subscribed to
        and that also appear in the subs_list list.

        Cached in self._common_subs

        :subs_list: QS or list of auth user's subreddit subscriptions.
        :fav_only: only consider objects in subs_list where is_favorite=True.
        """
        if settings.DEBUG:
            print('common_subs() called...')
        if not hasattr(self, '_common_subs'):
            self._set_common_not_common_subs(user, fav_only)

        return self._common_subs

    def get_not_common_subs(self, user, fav_only=True):
        """
        Return a list with the "not_common_subs" the instance user subscribed
        to and that DO NOT appear in the subs_list list.

        Cached in self._not_common_subs

        :subs_list: QS or list of auth user's subreddit subscriptions.
        :fav_only: only consider objects in subs_list where is_favorite=True.
        """
        if not hasattr(self, '_not_common_subs'):
            self._set_common_not_common_subs(user, fav_only)

        return self._not_common_subs

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

    @property
    def distance_km(self):
        return '{} km'.format(int(self.get_distance_in_km() * 100) / 100)

    @property
    def distance_mi(self):
        return '{} mi'.format(int(self.get_distance_in_miles() * 100) / 100)

    @property
    def gender(self):
        try:
            return [x[1] for x in settings.SEX if x[0] == self.sex][0]
        except IndexError:
            return ''

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
    is_favorite = models.BooleanField(default=True)  # user fav'd this sr.

    class Meta:
        verbose_name = "subreddit subscription"
        verbose_name_plural = "subreddit subscriptions"
        ordering = ['sr__display_name']

        # TODO: add this here, first clean up dupes.
        # unique_together = [user, sr]

    def __str__(self):
        return '{} --> {}'.format(self.user.username, self.sr.name)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile(user=instance)
        profile.name = instance.username
        try:
            profile.save()
        except:
            pass


class Visit(models.Model):
    """Remember the last visit of a user to another user's profile page."""
    visitor = models.ForeignKey(User, editable=False, related_name='visited',
                                db_index=True)
    host = models.ForeignKey(User, editable=False, related_name='was_visited',
                             db_index=True)
    created = models.DateTimeField(default=now)
    hidden = models.BooleanField(default=False)

    class Meta:
        verbose_name = "visit"
        verbose_name_plural = "visits"
        ordering = ['-created']

    def __str__(self):
        return '{} visited {}'.format(self.visitor.username,
                                      self.host.username)

    @classmethod
    def add_visitor_host(cls, visitor, host):
        Visit.objects.filter(visitor=visitor, host=host).delete()
        return Visit.objects.create(visitor=visitor, host=host)


class PushNotificationEndpoint(models.Model):
    """Store users push notification subscriptions for cloud messaging."""
    user = models.ForeignKey(User, related_name='endpoints')
    sub = models.CharField(max_length=2000, blank=False, unique=True)
    latest = models.DateTimeField(default=now)  # when the last notif. was send

    def __str__(self):
        return self.sub[:50]


class Message(models.Model):
    msg = models.CharField(max_length=240, blank=False, null=False)
    sender = models.ForeignKey(User, related_name='sent_messages')
    receiver = models.ForeignKey(User, related_name='received_messages')
    created = models.DateTimeField(default=now)

    class Meta:
        verbose_name = "private message"
        verbose_name_plural = "private messages"
        ordering = ['-id']

    def __str__(self):
        return '<Message: {} to {} on {}>'.format(
            self.sender.username, self.receiver.username, self.created)

    @classmethod
    def get_messages_list(cls, after, user1, user2):
        """Return a list of Message objects with created time larger than
        the "after" date. user_list is a list of exactly two users, both of
        which have to be present, either os sender or receiver."""
        messages = (Message.objects.filter(sender=user1, receiver=user2) |
                    Message.objects.filter(sender=user2, receiver=user1))
        if after:
            messages = messages.filter(id__gt=after)

        return messages.prefetch_related('sender', 'receiver')[:20]  # max 20
