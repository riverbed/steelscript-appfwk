# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.conf import settings

from rvbd_portal.apps.preferences.models import PortalUser

#from rvbd_portal.apps.preferences.models import UserProfile
#
#
#class UserProfileInline(admin.StackedInline):
#    model = UserProfile
#    can_delete = False
#
#
#class UserAdmin(UserAdmin):
#    inlines = (UserProfileInline, )
#
#admin.site.unregister(User)
#admin.site.register(settings.AUTH_USER_MODEL, UserAdmin)


class PortalUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    #fieldsets = (
     #   (None, {'fields': ('username', 'password')}),
     #   ('Personal info', {'fields': ('email', 'first_name',
     #                                 'last_name', 'timezone',)}),
     #   ('Permissions', {'fields': ('is_admin',)}),
     #   ('Important dates', {'fields': ('last_login',)}),
    #)

admin.site.register(PortalUser, PortalUserAdmin)

