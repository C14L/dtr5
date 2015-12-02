from django import template
from toolbox import meters_in_km, meters_in_miles
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter(name='prefdist')
def prefdist(val, arg):
    # {{v.profile.get_distance|prefdist:user}}
    if arg.profile.pref_distance_unit == 'km':
        return '{} km'.format(floatformat(meters_in_km(val), 1))
    elif arg.profile.pref_distance_unit == 'mi':
        return '{} miles'.format(floatformat(meters_in_miles(val), 1))


@register.filter(name='to_miles')
def to_miles(km):
    return meters_in_miles(km*1000)
