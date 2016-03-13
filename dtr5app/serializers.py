from django.contrib.auth.models import User
from rest_framework import serializers

from dtr5app.models import Profile, Subscribed


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'is_staff', 'is_superuser', 'profile', )


class SubscribedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscribed
        fields = ('sr', 'is_favorite', 'user_is_contributor', 'user_is_muted',
                  'user_is_moderator', 'user_is_subscriber', 'user_is_banned', )


class ProfileSerializer(serializers.ModelSerializer):
    """
    Limited to values that are accessible by any logged in user. To have a
    authenticated user view their own profile, use FullProfileSerializer below.
    """
    class Meta:
        model = Profile
        fields = ('created', 'updates', 'accessed',
                  'link_karma', 'comment_karma', 'has_verified_email',
                  'lat', 'lng', 'sex', 'about', 'herefor', 'tagline',
                  'height', 'weight', 'views_count', 'matches_count', )

        """
        computed_fields = ['age', 'pics', 'lookingfor', 'pref_distance_unit',
                           'display_background_pic',
                           'western_zodiac', 'western_zodiac_symbol',
                           'eastern_zodiac', 'eastern_zodiac_symbol',
                           'subscribed_subs']

        common_subs = get_common_subs
        not_common_subs = get_not_common_subs
        distance = get_distance
        is_match = match_with
        is_like = does_like
        is_nope = does_nope
        """


class FullProfileSerializer(ProfileSerializer):
    """
    Used for auth user's own profile view, so they can edit some values that
    not visible to other users when viewing the profile.
    """

    pass

    # 'f_sex', 'f_distance', 'f_minage', 'f_maxage', 'f_over_18',
    # 'f_has_verified_email', 'f_is_stable',
    # 'new_matches_count', 'new_matches_count', 'new_matches_count'



