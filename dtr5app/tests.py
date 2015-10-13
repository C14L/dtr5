import re
from django.conf import settings
from django.test import TestCase
from .utils import (get_usernames_around_view_user, )


class Dtr5appTestCase(TestCase):

    def test_get_usernames_around_view_user(self):
        userbuff = ['user1', 'user2', 'user3', 'user4', 'user5', 'user6',
                    'user7', 'user8', 'user9', 'user10', 'user11', 'user12',
                    'user13', 'user14', 'user15']

        result = get_usernames_around_view_user(userbuff, 'user8', 3)
        expected = ['user5', 'user6', 'user7', 'user8', 'user9', 'user10',
                    'user11']
        self.assertEqual(result, expected)

        result = get_usernames_around_view_user(userbuff, 'user3', 1)
        expected = ['user2', 'user3', 'user4']
        self.assertEqual(result, expected)

        result = get_usernames_around_view_user(userbuff, 'user1', 4)
        expected = ['user1', 'user2', 'user3', 'user4', 'user5']
        self.assertEqual(result, expected)

        result = get_usernames_around_view_user(userbuff, 'user15', 2)
        expected = ['user13', 'user14', 'user15']
        self.assertEqual(result, expected)

        result = get_usernames_around_view_user(userbuff, 'user11', 12)
        expected = userbuff
        self.assertEqual(result, expected)
