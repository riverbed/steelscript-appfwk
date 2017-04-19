from os.path import basename
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def filename(value):
    return basename(value)
