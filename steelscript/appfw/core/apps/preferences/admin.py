# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from steelscript.appfw.core.apps.preferences.models import PortalUser
from steelscript.appfw.core.apps.preferences.forms import (PortalUserCreationForm,
                                                PortalUserChangeForm)


class PortalUserAdmin(UserAdmin):
    form = PortalUserChangeForm
    add_form = PortalUserCreationForm

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Preferences', {'fields': ('timezone',)}),
        ('Personal info', {'fields': ('email', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

admin.site.register(PortalUser, PortalUserAdmin)
