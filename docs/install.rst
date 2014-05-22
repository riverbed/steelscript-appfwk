Installation
============

The SteelScript Application Framework is distributed entirely as
Python packages via the Python Package Index `PyPI
<https://pypi.python.org/pypi>`_.

Quick Install
-------------

Checklist:

1. ``steelscript`` installed (if not see :doc:`/index`)

2. Running Linux / Mac (for Windows, see `detailed`_)

3. Developer tools installed (gcc/g++ or the like)

If you can check off all of the above, simply run (in a `virtualenv
<http://www.virtualenv.org/>`_):

.. code:: bash

   $ steel install --appfwk

This will install all the additional packages related to the
Application Framework.  It may take some time, often 10 minutes or so,
it has to compile NumPy and Pandas packages.  (Tail the log in
~/.steelscript/steel.log if you want to see what's happening behind
the scenes).

.. _detailed:

Detailed Installation
---------------------

If you're familiar with ``pip`` and Python package
installation, the latest stable versions of these packages are hosted
on `PyPI`_ - the Python Package Index.

The following packages are related to the Application Framework:

* ``steelscript.appfwk``
  (`PyPI <https://pypi.python.org/pypi/steelscript.appfwk>`_,
  `GitHub
  <https://github.com/riverbed/steelscript-appfwk/releases>`_) -
  the core modules and data files for the Application Framework

* ``steelscript.wireshark``
  (`PyPI <https://pypi.python.org/pypi/steelscript.wireshark>`_,
  `GitHub
  <https://github.com/riverbed/steelscript-wireshark/releases>`_) -
  extensions to analyze PCAP files using Wireshark / tshark

* ``steelscript.appfwk.business-hours``
  (`PyPI <https://pypi.python.org/pypi/steelscript.appfwk.business-hours>`_,
  `GitHub
  <https://github.com/riverbed/steelscript-appfwk-business-hours/releases>`_) -
  adds support for running any report over business hours only

The primary package is ``steelscript-appfwk``.  Installing this will
pull in a number of dependencies.  The exact dependencies will change
over time as new features are added.  When installing via ``pip``,
the dependencies will be installed automatically.

Note that the base packages such as ``steelscript.netprofiler`` and
``steelscript.netshark`` include support for the Application
Framework.

There are two packages dependencies that deserve special attention:

* `Python Pandas <http://pandas.pydata.org/>`_ (`package
  <https://pypi.python.org/pypi/pandas/0.13.1/>`_) - Python Data
  Analysis Library

* `NumPy <http://www.numpy.org/>`_ (`package
  <https://pypi.python.org/pypi/numpy>`_) - scientific computing with
  Python

These packages are heavily used for data tables and manipulation.
Both packages have large portions written in C for performance, thus
they must be compiled.  For Linux / Mac, it is usually sufficient just
to insure that the developer tools are installed.  For Windows, it is
best to install these packages from pre-compiled distributions (see
their respective web sites).

.. note::

   Installing numpy and pandas packages can often take a
   significant amount of time (~10 minutes).  During compilation
   it is normal to see numerous warnings go by.

For complete instructions for your platform, follow the installation
instructions for SteelScript adding ``steelscript.appfwk`` to your list:

* :doc:`/install/quick`
* :doc:`/install/linuxmac`
* :doc:`/install/windows`

You can check your installation using ``steel about``:

.. code-block:: bash

   $ steel about

   Installed SteelScript Packages
   Core packages:
     steelscript                               0.6.0.post43
     steelscript.netprofiler                   0.6.0.post23
     steelscript.netshark                      0.6.0.post21
     steelscript.wireshark                     0.0.1

   Application Framework packages:
     steelscript.appfwk                        0.1.0.post34
     steelscript.appfwk.business-hours         0.1.0.post17

   Paths to source:
     /Users/admin/env/ss/lib/python2.7/site-packages
