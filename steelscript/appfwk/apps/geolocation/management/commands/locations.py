# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import csv

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from steelscript.appfwk.apps.geolocation.models import Location, LocationIP


# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")


class Command(BaseCommand):
    help = 'Manage locations'

    def add_arguments(self, parser):
        group = parser.add_argument_group("Location Help",
                                          "Helper commands to manage "
                                          "locations")
        group.add_argument('--import-locations',
                           action='store',
                           dest='import_locations',
                           default=False,
                           help='Import Locations: location,latitude,'
                                'longitude')

        group.add_argument('--import-location-ip',
                           action='store',
                           dest='import_location_ip',
                           default=False,
                           help='Import Location / IP map: location,ip,mask')

        group.add_argument('--merge',
                           action='store_true',
                           dest='merge',
                           default=False,
                           help='Merge import file rather than replace')

    def handle(self, *args, **options):
        """ Main command handler. """

        merge = options['merge']

        if options['import_locations']:
            filename = options['import_locations']

            with transaction.atomic():

                count_new = 0
                count_updated = 0

                if not merge:
                    Location.objects.all().delete()

                with open(filename, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        name = row[0]
                        latitude = float(row[1])
                        longitude = float(row[2])

                        try:
                            location = Location.objects.get(name=name)
                            count_updated += 1
                        except ObjectDoesNotExist:
                            location = Location(name=name)
                            count_new += 1

                        location.latitude = latitude
                        location.longitude = longitude
                        location.save()

            if merge:
                self.stdout.write('Imported %d new locations, %d updated' %
                                  (count_new, count_updated))
            else:
                self.stdout.write('Imported %d locations' % count_new)

        if options['import_location_ip']:
            filename = options['import_location_ip']

            with transaction.atomic():

                count_new = 0
                count_updated = 0

                if not merge:
                    LocationIP.objects.all().delete()

                with open(filename, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        name = row[0]
                        address = row[1]
                        mask = row[2]

                        try:
                            location = Location.objects.get(name=name)
                        except ObjectDoesNotExist:
                            raise KeyError('Unknown location: %s' % name)

                        try:
                            location_ip = LocationIP.objects.get(
                                location=location, address=address, mask=mask)
                            count_updated += 1
                        except ObjectDoesNotExist:
                            location_ip = LocationIP(location=location,
                                                     address=address,
                                                     mask=mask)
                            count_new += 1

                        location_ip.save()

            if merge:
                self.stdout.write('Imported %d new locations/ip entries, %d updated' %
                                  (count_new, count_updated))
            else:
                self.stdout.write('Imported %d locations/ip entries' % count_new)
