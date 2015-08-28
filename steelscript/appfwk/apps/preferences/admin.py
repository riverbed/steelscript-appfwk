# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from steelscript.appfwk.apps.preferences.models import AppfwkUser
from steelscript.appfwk.apps.preferences import forms


class AppfwkUserAdmin(UserAdmin):
    form = forms.AppfwkUserChangeForm
    add_form = forms.AppfwkUserCreationForm

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

admin.site.register(AppfwkUser, AppfwkUserAdmin)
