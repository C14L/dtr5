"""
Loop though all users and download their first pic from whereever it is hosted,
and store it locally for later upload to reddmeet, using "raw/username.jpg" as
filename for each user's picture respectively.

Wait some 5 - 10 seconds between hits to the same host, to be very easy on the
originating servers.
"""
from time import sleep

import os
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from os import path
from random import randrange
from requests.exceptions import ConnectionError


class Command(BaseCommand):
    help = 'Download the first picture of every user to store locally.'

    target_dir = path.join(settings.BASE_DIR, 'avatars', 'raw')

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', dest='save',
                            default=False, help='Save changes to Profile table')

    def handle(self, *args, **options):
        os.makedirs(self.target_dir, mode=0o755, exist_ok=True)

        users = User.objects.filter(is_active=True)\
                            .filter(last_login__isnull=False)\
                            .exclude(profile___pics='')\
                            .order_by('date_joined')\
                            .prefetch_related('profile')

        print('Found {} profiles.'.format(users.count()))
        i, j = self._download_raw_files(users)
        print('Done! {} users processes and {} files downloaded.'.format(i, j))

    def _download_raw_files(self, users):
        i, j = 0, 0

        for user in users:
            i += 1
            try:
                url = user.profile.pics[0]['url']
            except IndexError:
                continue

            print('{:04d} {}'.format(i, url), end=' ', flush=True)

            # Check if the output file already exists
            filename = '{}.jpg'.format(user.username)
            target_file = path.join(self.target_dir, filename)
            if path.isfile(target_file):
                print('exists.', flush=True)
                continue

            # Download the actual file
            try:
                self._download_file(url, target_file)
                j += 1
                print('--> {} ok.'.format(filename), flush=True)
            except KeyboardInterrupt:
                print('Interrupted, terminating script...', flush=True)
                return i, j
            except ConnectionError:
                print('Network error.', flush=True)

            sleep(randrange(5, 10))
        return i, j

    def _download_file(self, url, target_file):
        r = requests.get(url, stream=True)
        print('{}'.format(r.status_code), end=' ', flush=True)

        # Create file even on network error to avoid trying to download it
        # again on next run. Download errors seem to happen on Fb links mostly,
        # maybe Fb blocks crawlers from accessing their images.
        with open(target_file, "wb") as fh:
            if r.status_code == 200:
                print('{}'.format(r.headers['content-type']), end=' ', flush=True)
                for data in r.iter_content():
                    fh.write(data)

                return r.status_code

        print('ERROR', end=' ', flush=True)
        return False
