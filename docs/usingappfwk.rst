Using the Application Framework
===============================

Once your :doc:`project has been created <projects>` and initialized,
devices :ref:`have been added <devices>`, :ref:`user preferences <user preferences>`
have been set, and :ref:`system settings <system settings>` have been defined, you
are ready to run a report!


Logging In
----------

All pages in App Framework require a valid login for access.  Some, as described
in :doc:`configuration` require admin user permissions, but all others are
accessible to any logged in user.


Running Reports
---------------

Choosing one of the reports under the "Reports" drop-down menu brings up
a new page with a Criteria form.  The elements contained in this form will
vary from report to report, but typically it will include some combination
of the following:

    * *End Time* - The date and time for all widgets in the report to end
      at.  Some reports can have different time ranges for different widgets,
      but they will all end at the same time.  The icons to the right of
      each box will update that element to the current value (date or time).
    * *Filter Expression* - Many reports include a filter expression for
      one of the included devices.  A info icon should provide additional
      clarification of the type of expression that can be input here.
    * *Device Selection* - Each device used in the report will have a
      dropdown to choose the specific device instance to use.  For example,
      many organizations have multiple Sharks installed, if each of those
      have been defined in the :ref:`devices <devices>` interface, then
      they will all be included as valid options in the NetShark dropdown
      field.  Additionally, NetShark devices allow choosing the specific
      Capture Job to be used for that report.

After setting the criteria as desired (in many cases the defaults are fine),
click run and several jobs will be kicked off on the server.  You will see widget
boxes appear with spinning icons while the jobs are processed and the data
retrieved.  As data becomes available for each widget it will update.


