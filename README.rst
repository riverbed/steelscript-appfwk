Riverbed SteelScript Application Framework
==========================================

The SteelScript Application Framework makes it easy to create a fully
custom web application that mashes up data from multiple sources.  It comes
pre-configured with several reports for NetProfiler and NetShark.

For a complete guide to installation, see:

  `https://support.riverbed.com/apis/steelscript/index.html <https://support.riverbed.com/apis/steelscript/index.html>`_

Quick Start
-----------

If you already have pip, just run the following (in a
`virtualenv <http://www.virtualenv.org/>`_):

.. code:: bash

   $ pip install steelscript
   $ steel install

Not sure about pip, but you know you have Python?

1. Download ``steel_bootstrap.py`` `from here <https://support.riverbed.com/apis/steelscript/index.html#quick-start>`_

2. Run it (in a `virtualenv <http://www.virtualenv.org/>`_):

   .. code:: bash

      $ python steel_bootstrap.py install

Once you have the base ``steelscript`` package installed, getting started
is just a few commands away:

.. code:: bash

   $ steel install --appfwk
   $ steel appfwk mkproject

This will populate a local directory with all the files you need to run
the server in "dev" mode on your local system.

For next steps, see the full documentation guide:

  `https://support.riverbed.com/apis/steelscript/index.html <https://support.riverbed.com/apis/steelscript/index.html>`_

License
=======

Copyright (c) 2015 Riverbed Technology, Inc.

SteelScript-appfwk is licensed under the terms and conditions of the MIT
License accompanying the software ("License").  SteelScript-appfwk is
distributed "AS IS" as set forth in the License.  SteelScript-appfwk also
includes certain third party code.  All such third party code is also
distributed "AS IS" and is licensed by the respective copyright holders under
the applicable terms and conditions (including, without limitation, warranty
and liability disclaimers) identified in the license notices accompanying the
software.


