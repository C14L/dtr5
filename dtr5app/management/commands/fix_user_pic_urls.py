"""

"""
from time import sleep

from django.contrib.auth.models import User
from django.core.management import BaseCommand
from random import randrange

from toolbox_imgur import extract_image_src, re_topic
from toolbox_imgur import re_album, re_gallery, re_noext, re_srpic


class Command(BaseCommand):
    help = 'Download the first picture of every user to store locally.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)\
                            .filter(last_login__isnull=False)\
                            .exclude(profile___pics='')\
                            .order_by('date_joined')\
                            .prefetch_related('profile')

        print('Found {} profiles.'.format(users.count()))
        i, j, k = self._fix_user_pic_urls(users)
        print('Done with {} / {} items, {} updated.'.format(i, j, k))

    def _fix_user_pic_urls(self, users):
        i, j, k = 0, 0, 0

        for user in users:
            j += 1
            if len(user.profile.pics) < 1:
                continue

            # Here, user.profile.pics is a @propery, so any changes to it have
            # to be asigned using eq (=). Changing individual items in the list
            # would have no effect. So, make a copy of the list to work on, and
            # then asign the entire list back to the @property when done.
            pics = user.profile.pics[:]
            dirty = False

            for pic in pics:
                i += 1
                url = self._get_fixed_url(pic['url'])

                if url != pic['url']:
                    print('{:04d} {} --> {}'.format(i, pic['url'], url))
                    pic['url'] = url
                    dirty = True
                    sleep(randrange(1, 2))

            if dirty:
                # At least one pic[url] value changed. Write item to db.
                user.profile.pics = pics
                user.profile.save(update_fields=['_pics'])
                k += 1

        return i, j, k

    def _get_fixed_url(self, url):
        """
        Mostly returns the same URL it gets. But in some well-defined cases,
        such as an album URL or a gallery URL, it will try to convert it into
        an actual picture URL.
        """
        size = 'm'
        base = 'https://i.imgur.com/'

        if re_album.search(url):
            url = extract_image_src(url, size)
        elif re_gallery.search(url):
            url = extract_image_src(url, size)
        elif re_topic.search(url):
            url = extract_image_src(url, size)
        elif re_noext.search(url):
            partial = url.rsplit('/', 1)[1]
            url = '{}{}{}.jpg'.format(base, partial, size)
        elif re_srpic.search(url):
            partial = url.rsplit('/', 1)[1]
            url = '{}{}{}.jpg'.format(base, partial, size)

        return url
