# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from steelscript.appfwk.apps.preferences.models import PortalUser, SystemSettings


class UserProfileForm(forms.ModelForm):
    """ Used for normal user updates. """
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = get_user_model()
        fields = ('email', 'timezone')


class PortalUserCreationForm(forms.ModelForm):
    """ Create unprivileged user. """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = PortalUser

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(PortalUserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class PortalUserChangeForm(forms.ModelForm):
    """ Update user form. """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = PortalUser

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class SystemSettingsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SystemSettingsForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SystemSettings
        widgets = {'maps_version': forms.HiddenInput(),
                   'maps_api_key': forms.HiddenInput()}

    def clean(self):
        # check for API key if maps are either FREE or BUSINESS
        cleaned_data = super(SystemSettingsForm, self).clean()
        version = cleaned_data.get('maps_version')
        api_key = cleaned_data.get('maps_api_key')

        if not api_key and version in ('FREE', 'BUSINESS'):
            if version == 'FREE':
                msg = u'Usage of Free version of Google Maps requires API Key'
            else:
                msg = u'Usage of Business version of Google Maps requires API Key'
            self._errors['maps_api_key'] = self.error_class([msg])
            del cleaned_data['maps_api_key']

        return cleaned_data
