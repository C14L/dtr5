"""
Collection of random simple general-purpose helper functions.
"""

import re


def force_int(x, min=None, max=None):
    """
    Receives any value and returns an integer. Values that can not be
    parsed are returned as 0. Values that are smaller that min or
    larger than max, if either is given, are set to min or max
    respectively.
    """
    try:
        i = int(x)
    except:
        return 0
    if min and i < min:
        i = min
    if max and i > max:
        i = max
    return i


def force_float(x):
    """
    Receives any value and returns a float. Values that can not be
    parsed are returned as 0.0
    """
    try:
        return float(x)
    except:
        return 0


def set_imgur_url(url="http://i.imgur.com/wPqDiEy.jpg", size='t'):
    """
    Gets a imgur picture URL (e.g. "http://i.imgur.com/wPqDiEyl.jpg")
    and changes the size byte to 'size':
      - "s" small rectangular
      - "t" thumb
      - "m" medium
      - "l" large
      - "" original upload size

    If 'url' is not a valid imgur.com URL, the value is returned
    unchanged.
    """
    re_imgur_url = (r'(?P<base>https?://i.imgur.com/)'
                    r'(?P<name>[a-zA-Z0-9]{2,20}?)'
                    r'(?P<size>[stml]?)\.'
                    r'(?P<ext>jpe?g|gif|png|webp)')
    m = re.search(re_imgur_url, url)
    if m:
        url = '{}{}{}.{}'.format(m.group('base'), m.group('name'),
                                 size, m.group('ext'))
    return url


def get_imgur_page_from_picture_url(url):
    """
    Returns the URL of the containing page for a picture URL
    on imgur.com
    """
    re_imgur_url = (r'(?P<base>https?://i.imgur.com/)'
                    r'(?P<name>[a-zA-Z0-9]{2,20})'
                    r'(?P<size>[stml]?)\.'
                    r'(?P<ext>jpe?g|gif|png|webp)')
    m = re.search(re_imgur_url, url)
    if m:
        base = m.group('base').replace('i.', '')
        return '{}{}'.format(base, m.group('name'))
    else:
        return ''
