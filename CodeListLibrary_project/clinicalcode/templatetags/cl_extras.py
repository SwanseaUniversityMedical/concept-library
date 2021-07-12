
from django import template

register = template.Library()


@register.filter
def cut(value, arg):
    """Removes all occurrences of arg from the given string"""
    return value.replace(arg, '')


@register.filter
def islist(value):
    """Check if value is of type list"""
    print(value)
    print(type(value) == list)
    return type(value) == list




