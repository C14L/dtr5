from datetime import date
from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase
from dtr5app.models import Profile


class Dtr5appModelsTestCase(TestCase):
    username1 = 'testuser1'
    username2 = 'testuser2'
    sr_list = \
        'bestof announcements Art AskReddit askscience aww blog books creepy ' \
        'dataisbeautiful DIY Documentaries EarthPorn explainlikeimfive Fitness'\
        ' food funny Futurology gadgets gaming GetMotivated gifs history IAmA '\
        'InternetIsBeautiful Jokes LifeProTips listentothis mildlyinteresting '\
        'movies Music news nosleep nottheonion OldSchoolCool personalfinance ' \
        'philosophy photoshopbattles pics science Showerthoughts space sports '\
        'television tifu todayilearned TwoXChromosomes UpliftingNews videos '  \
        'worldnews WritingPrompts'
    sr_list_short = 'Music news nosleep Jokes LifeProTips listentothis'

    def setUp(self):
        User.objects.all().delete()
        Profile.objects.all().delete()
        self.user1 = User.objects.create(username=self.username1)
        self.user2 = User.objects.create(username=self.username2)

    def tearDown(self):
        pass

    def test_profile_created_destroyed_with_user(self):
        username = 'testuser74598'

        with transaction.atomic():
            count = User.objects.filter(username=username).count()
        self.assertEqual(count, 0)

        with transaction.atomic():
            u1 = User.objects.create(username=username)
        self.assertTrue(isinstance(u1, User))

        with transaction.atomic():
            c1 = User.objects.filter(username=username).count()
        self.assertEqual(1, c1)

        with transaction.atomic():
            self.assertEqual(1, Profile.objects.filter(pk=u1).count())

        with transaction.atomic():
            u1.delete()

        with transaction.atomic():
            self.assertEqual(0, Profile.objects.filter(pk=u1).count())

    def test_long_username(self):
        usernames = ('x'*19, 'x'*20, 'x'*21, )

        for i in range(3):
            with transaction.atomic():
                User.objects.create(username=usernames[i])

        # First 2 values must pass.
        for i in range(2):
            with transaction.atomic():
                user = User.objects.get(username=usernames[i])
                self.assertEqual(usernames[i], user.username)

        # Last value must fail.
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(username=usernames[2])

    def test_profile_returns_username(self):
        username = 'testuser78002383'

        with transaction.atomic():
            u1 = User.objects.create(username=username)
        self.assertEqual(username, str(u1.profile))

        with transaction.atomic():
            u2 = User.objects.get(username=username)
        self.assertEqual(username, str(u2.profile))

    def test_profile_property_f_ignore_sr_li(self):
        with transaction.atomic():
            self.user1.profile.f_ignore_sr_li = self.sr_list
            self.user1.profile.save()
        with transaction.atomic():
            li = Profile.objects.get(pk=self.user1.pk)._f_ignore_sr_li
        self.assertEqual(li, self.sr_list)

    def test_profile_dob_age(self):
        dob1 = date(1995, 1, 1)
        dob2 = date(1990, 1, 1)
        self.user1.profile.dob = dob1
        self.user2.profile.dob = dob2
        diff = self.user2.profile.get_age() - self.user1.profile.get_age()
        self.assertEqual(5, diff)
