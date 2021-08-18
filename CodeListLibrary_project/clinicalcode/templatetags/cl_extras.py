
from django import template

register = template.Library()


@register.filter
def cut(value, arg):
    """Removes all occurrences of arg from the given string"""
    return value.replace(arg, '')


@register.filter
def islist(value):
    """Check if value is of type list"""
    return type(value) == list


@register.filter
def tolist(value, arg):
    """Convert comma separated value to a list of type arg"""
    
    if arg == "int":
        return [int(t) for t in value.split(',')]
    else:
        return [str(t) for t in value.split(',')]


@register.filter
def toString(value):
    """Convert value to string"""
    return str(value)


@register.filter
def addStr(value, arg):
    """concatenate value & arg"""
    return str(value) + str(arg)