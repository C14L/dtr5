"""
Loop though all downloaded raw user pictures and create the two standard sizes
from each file (/s/=100x100 and /m/=600x600) and save them as JPEG.
"""
import os
from django.conf import settings
from os.path import join
from django.core.management import BaseCommand

from dtr5app.utils_pics import create_public_pics_for_every_raw_file, \
    check_public_files_all_have_a_raw_file, check_raw_files_have_active_user


class Command(BaseCommand):
    help = 'Convert downloaded user pics into their sizes and JPG format.'

    base_dir = join(settings.BASE_DIR, 'avatars')
    raw_dir = join(base_dir, 'raw')
    sizes = {'s': '100x100', 'm': '400x400'}

    def handle(self, *args, **options):
        # Make sure the picture dirs exist.
        for n in self.sizes.keys():
            os.makedirs(join(self.base_dir, n), mode=0o755, exist_ok=True)

        # Run all picture file checks
        args = [self.base_dir, self.raw_dir, self.sizes]
        check_raw_files_have_active_user(*args)
        check_public_files_all_have_a_raw_file(*args)
        create_public_pics_for_every_raw_file(*args)
