# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin


class UtilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'path', 'islogfile')

#admin.site.register(Utility, UtilityAdmin)


class ResultsAdmin(admin.ModelAdmin):
    pass

#admin.site.register(Results, ResultsAdmin)


class ParameterAdmin(admin.ModelAdmin):
    pass

#admin.site.register(Parameter, ParameterAdmin)


class ConsoleJobAdmin(admin.ModelAdmin):
    pass

#admin.site.register(ConsoleJob, ConsoleJobAdmin)
