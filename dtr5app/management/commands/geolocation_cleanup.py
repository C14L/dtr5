"""
Clean up common errors in manually input geo location data.
"""

from django.core.management.base import BaseCommand, CommandError
from dtr5app.models import Profile


class Command(BaseCommand):
    help = 'Clean up common errors in manually input geo location data.'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', dest='save',
                            default=False, help='Save changes to Profile table')

    def handle(self, *args, **options):
        count = self._fix_lng_for_central_asia_to_usa(save=options['save'])
        self.stdout.write('Cleaned up {} profiles.'.format(count))

        if options['save']:
            self.stdout.write('All changes saved to Profile table.')
        else:
            self.stdout.write('!! Not saved yet !!')
            self.stdout.write('Use --save argument to persist the changes.')

    def _fix_lng_for_central_asia_to_usa(self, save=False):
        """
        Some North Americans have located themselves in central Asia and
        western China, because they used positive instead of negative "lng"
        value. Find them, and for "lat/lng" values with 6 or less decimal
        digits, convert the "lng" value to negative.

        :Return: the number of rows changed.
        """
        count = 0
        limit = 9
        all = Profile.objects.filter(lat__gte=25.0, lat__lte=57.0) \
                             .filter(lng__gte=68.8, lng__lte=123.5)
        for p in all:
            if len(str(p.lat)) <= limit:
                nlng = p.lng * (-1)
                s = 'User:{:5d} has lat:{:>10}, lng:{:>10} -> lng:{:11}'
                print(s.format(p.user_id, p.lat, p.lng, nlng))
                p.lng = nlng
                if save:
                    p.save()
                count += 1

        return count
