GeoLocation
===========

The GeoLocation builtin plugin defines two database tables that are
used by other modules:

* Locations - maps location names to latitude and longitude
* LocationIP - maps IP addresses or subnets to locations names

Admin Panel
-----------

Both databases are accessible via the Admin panel as shown below:

.. image:: geolocation-admin.png
   :align: center
   :scale: 30%
   :width: 772
   :height: 460

This allows you to add, modify or remove entries from the database.
The "name" field between should be the same for the same locations.

Importing from the command line
-------------------------------

Both databases can be imported from the command line using ``python
manage.py locations``:

.. code-block:: console

   $ python manage.py locations -h
   Usage: manage.py locations [options] None

   Manage locations

     Location Help:
       Helper commands to manange locations

       --import-locations=IMPORT_LOCATIONS
                           Import Locations: location,latitude,longitude
       --import-location-ip=IMPORT_LOCATION_IP
                           Import Location / IP map: location,ip,mask
       --merge             Merge import file rather than replace

There are sample files in the ``example-configs`` directory.  A
snippet of each is shown below.

.. code-block:: console

   $ python manage.py locations --import-locations example-configs/sample_locations.txt
   Imported 13 locations

   $python manage.py locations --import-location-ip example-configs/sample_location_ip.txt
   Imported 13 locations/ip entries

Sample Locations
~~~~~~~~~~~~~~~~

.. code-block:: console

   "Seattle",47.6097,-122.3331
   "LosAngeles",34.0522,-118.2428
   "Phoenix",33.43,-112.02
   "Columbus",40.00,-82.88
   "SanFrancisco",37.75,-122.68
   "Austin",30.30,-97.70
   "Philadelphia",39.88,-75.25
   "Hartford",41.73,-72.65
   "DataCenter",35.9139,-81.5392
   "Singapore",1.28967,103.8500700
   "Cambridge",42.3603,-71.0893
   "Champaign",40.1164200,-88.2433800
   "NYC",40.7142700,-74.0059700

Sample Location-IP
~~~~~~~~~~~~~~~~~~

.. code-block:: console

   "Seattle","10.99.11.0","255.255.255.0"
   "LosAngeles","10.99.12.0","255.255.255.0"
   "Phoenix","10.99.13.0","255.255.255.0"
   "Columbus","10.99.14.0","255.255.255.0"
   "SanFrancisco","10.99.15.0","255.255.255.0"
   "Austin","10.99.16.0","255.255.255.0"
   "Philadelphia","10.99.17.0","255.255.255.0"
   "Hartford","10.99.18.0","255.255.255.0"
   "DataCenter","10.100.0.0","255.255.0.0"
   "Singapore","10.100.0.0","255.255.0.0"
   "Cambridge","10.100.0.0","255.255.0.0"
   "Champaign","10.100.0.0","255.255.0.0"
   "NYC","10.100.0.0","255.255.0.0"
