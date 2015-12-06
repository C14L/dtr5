from django import template
from django.template.defaultfilters import floatformat
from toolbox import meters_in_km, meters_in_miles

register = template.Library()


@register.filter(name='prefdist')
def prefdist(val, arg):
    """
    Example: {{v.profile.get_distance|prefdist:user}}

    :val: distance in meters
    :arg: User instance who's pref_distance_unit setting to use
    """
    if arg.profile.pref_distance_unit == 'km':
        return '{} km'.format(floatformat(meters_in_km(val), 1))
    elif arg.profile.pref_distance_unit == 'mi':
        return '{} miles'.format(floatformat(meters_in_miles(val), 1))


@register.filter(name='prefdist_km')
def prefdist_km(val, arg):
    """Same as above, but val is in km."""
    return prefdist(val * 1000, arg)


@register.filter(name='to_miles')
def to_miles(km):
    return meters_in_miles(km*1000)


@register.filter(name='display_choice')
def display_choice(val, arg):
    return [x[1] for x in arg if x[0] == val][0]
