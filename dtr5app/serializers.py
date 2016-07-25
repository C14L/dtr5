from django.contrib.auth.models import User
from rest_framework import serializers

from dtr5app.models import Profile, Subscribed, Sr


class ViewSrSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sr
        fields = ('display_name', 'created', 'url', 'over18', 'lang',
                  'subreddit_type', 'subscribers', 'subscribers_here')


class SubscribedSerializer(serializers.ModelSerializer):
    sr = serializers.SlugRelatedField(many=False, read_only=True,
                                      slug_field='name')

    class Meta:
        model = Subscribed
        fields = ('sr', 'is_favorite', 'user_is_contributor', 'user_is_muted',
                  'user_is_moderator', 'user_is_subscriber', 'user_is_banned', )


class BasicUserProfileSerializer(serializers.ModelSerializer):
    """Just some very basic profile data, for lists or prev-next views."""
    pic = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('accessed', 'link_karma', 'comment_karma', 'lat', 'lng',
                  'sex', 'age', 'pic')

    def get_pic(self, obj):
        try:
            return obj.pics[0]['url']
        except IndexError:
            return ''


class BasicUserSerializer(serializers.ModelSerializer):
    """Just some very basic user data, for lists or prev-next views."""
    profile = BasicUserProfileSerializer(many=False, read_only=True)
    flag_created = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'profile', 'flag_created', 'flag_created')


class ViewUserProfileSerializer(serializers.ModelSerializer):
    """
    Limited to values that are accessible by any logged in user. To have a
    authenticated user view their own profile, use FullProfileSerializer below.
    """
    class Meta:
        model = Profile
        fields = ('created', 'updated', 'accessed',
                  'link_karma', 'comment_karma', 'has_verified_email',
                  'lat', 'lng', 'sex', 'about', 'herefor', 'tagline',
                  'height', 'weight', 'views_count', 'matches_count',
                  'age', 'distance_km', 'distance_mi', 'pics', 'gender',
                  )

        """
        computed_fields = [, 'lookingfor', 'pref_distance_unit',
                           'display_background_pic',
                           'western_zodiac', 'western_zodiac_symbol',
                           'eastern_zodiac', 'eastern_zodiac_symbol',
                           'subscribed_subs']
        """


class ViewUserSerializer(serializers.ModelSerializer):
    profile = ViewUserProfileSerializer(many=False, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'is_staff', 'is_superuser', 'profile', )


class AuthProfileSerializer(serializers.ModelSerializer):
    """
    Used for auth user's own profile view, so they can edit some values that
    not visible to other users when viewing the profile.
    """
    class Meta:
        model = Profile
        fields = ('created', 'updated', 'accessed',
                  'link_karma', 'comment_karma', 'has_verified_email',
                  'lat', 'lng', 'fuzzy', 'sex', 'about', 'herefor', 'tagline',
                  'height', 'weight', 'views_count', 'matches_count',
                  'dob', 'pics', )


class AuthUserSerializer(serializers.ModelSerializer):
    profile = AuthProfileSerializer(many=False, read_only=False)
    subs = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name',
                  'is_staff', 'is_superuser', 'profile', 'subs')
        read_only_fields = ('id', 'username', 'is_staff', 'is_superuser',
                            'subs')

    # noinspection PyMethodMayBeStatic
    def get_subs(self, obj):
        li = Sr.objects.filter(users__user=obj.id)
        return li.values_list('display_name', flat=True)

    def update(self, instance, validated_data):
        # User can only update fields in Profile instance. The username and
        # subs are taken from their Reddit profile.

        instance.profile.fuzzy = validated_data['profile']['fuzzy']
        instance.profile.save()

        return instance
