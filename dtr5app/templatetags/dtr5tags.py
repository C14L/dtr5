from django import template
from django.template.defaultfilters import floatformat
from toolbox import meters_in_km, meters_in_miles

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):
    """
    Simplefy pagination for URLs with GET parameters, by only replacing (or
    adding if necessary) only a single parameter's value.

    Usage:
        <a href="?{% url_replace request 'page' paginator.next_page_number %}">

    Source:
        http://stackoverflow.com/a/16609498/5520354
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


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
    """Return the display string of the choice item."""
    return [x[1] for x in arg if x[0] == val][0]
