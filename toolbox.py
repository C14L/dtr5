"""
Collection of random simple general-purpose helper functions.
"""

from datetime import date, datetime
import dateutil.parser
import math
import pytz
import re


def to_iso8601(when=None):
    """Return a datetime as string in ISO-8601 format."""
    if not when:
        when = datetime.now(pytz.utc)
    if not when.tzinfo:
        when = pytz.utc.localize(when)
    _when = when.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    return _when


def from_iso8601(when=None):
    """
    Return a UTC timezone aware datetime object from a string in
    ISO-8601 format.
    """
    if not when:
        _when = datetime.now(pytz.utc)
    else:
        _when = dateutil.parser.parse(when)
    if not _when.tzinfo:
        _when = pytz.utc.localize(_when)
    return _when


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


# --- Date of Birth and Zodiac -------------------------------------- #


def get_dob_range(minage, maxage):
    """Return earliest and latest dob to match a min/max age range."""
    year = date.today().year
    dob_earliest = date.today().replace(year=(year-maxage))
    dob_latest = date.today().replace(year=(year-minage))
    return dob_earliest, dob_latest


WESTERN_ZODIAC = (
    (0, ''), (1, 'aries'), (2, 'taurus'), (3, 'gemini'),
    (4, 'cancer'), (5, 'leo'), (6, 'virgo'), (7, 'libra'), (8, 'scorpio'),
    (9, 'sagittarius'), (10, 'capricorn'), (11, 'aquarius'), (12, 'pisces'))

WESTERN_ZODIAC_SYMBOLS = (
    (1, '♈'), (2, '♉'), (3, '♊'), (4,  '♋'), (5,  '♌'), (6,  '♍'),
    (7, '♎'), (8, '♏'), (9, '♐'), (10, '♑'), (11, '♒'), (12, '♓'))

WESTERN_ZODIAC_UPPER_LIMIT = (
    (120, 10), (218, 11), (320, 12), (420, 1), (521, 2), (621, 3), (722, 4),
    (823, 5), (923, 6), (1023, 7), (1122, 8), (1222, 9), (1231, 10))

EASTERN_ZODIAC = (
    (0, ''), (1, 'rat'), (2, 'ox'), (3, 'tiger'), (4, 'rabbit'),
    (5, 'dragon'), (6, 'snake'), (7, 'horse'), (8, 'goat'),
    (9, 'monkey'), (10, 'rooster'), (11, 'dog'), (12, 'pig'))

EASTERN_ZODIAC_SYMBOLS = (
    (1, '鼠'), (2, '牛'), (3, '虎'), (4, '兔'), (5, '龍'), (6, '蛇'),
    (7, '馬'), (8, '羊'), (9, '猴'), (10, '鷄'), (11, '狗'), (12, '猪'))

EASTERN_ZODIAC_UPPER_LIMIT = (  # from 1925-01-23 until 2044-01-29
    (19250123, 1), (19260212,  2), (19270201,  3), (19280122,  4),
    (19290209, 5), (19300129,  6), (19310216,  7), (19320205,  8),
    (19330125, 9), (19340213, 10), (19350203, 11), (19360123, 12),
    (19370210, 1), (19380130,  2), (19390218,  3), (19400207,  4),
    (19410126, 5), (19420214,  6), (19430204,  7), (19440124,  8),
    (19450212, 9), (19460201, 10), (19470127, 11), (19480209, 12),
    (19490128, 1), (19500216,  2), (19510205,  3), (19520126,  4),
    (19530213, 5), (19540202,  6), (19550123,  7), (19560211,  8),
    (19570130, 9), (19580217, 10), (19590207, 11), (19600127, 12),
    (19610214, 1), (19620204,  2), (19630124,  3), (19640212,  4),
    (19650201, 5), (19660120,  6), (19670208,  7), (19680129,  8),
    (19690216, 9), (19700205, 10), (19710126, 11), (19720214, 12),
    (19730202, 1), (19740122,  2), (19750210,  3), (19760130,  4),
    (19770217, 5), (19780206,  6), (19790127,  7), (19800215,  8),
    (19810204, 9), (19820124, 10), (19830212, 11), (19840201, 12),
    (19850219, 1), (19860208,  2), (19870128,  3), (19880216,  4),
    (19890205, 5), (19900126,  6), (19910214,  7), (19920203,  8),
    (19930122, 9), (19940209, 10), (19950130, 11), (19960218, 12),
    (19970206, 1), (19980127,  2), (19990215,  3), (20000204,  4),
    (20010123, 5), (20020211,  6), (20030131,  7), (20040121,  8),
    (20050208, 9), (20060128, 10), (20070217, 11), (20080206, 12),
    (20090125, 1), (20100213,  2), (20110202,  3), (20120122,  4),
    (20130209, 5), (20140130,  6), (20150218,  7), (20160207,  8),
    (20170127, 9), (20180215, 10), (20190204, 11), (20200124, 12),
    (20210211, 1), (20220131,  2), (20230121,  3), (20240209,  4),
    (20250128, 5), (20260216,  6), (20270205,  7), (20280125,  8),
    (20290212, 9), (20300202, 10), (20310122, 11), (20320210, 12),
    (20330130, 1), (20340218,  2), (20350207,  3), (20360127,  4),
    (20370214, 5), (20380203,  6), (20390123,  7), (20400211,  8),
    (20410131, 9), (20420121, 10), (20430209, 11), (20440129, 12))


def get_western_zodiac_index(dob):
    """Gets a datetime.date value and returns its Western zodiac index"""
    try:
        mdd = int(dob.strftime('%m%d'))
        lim = WESTERN_ZODIAC_UPPER_LIMIT
        return [e[1] for e in lim if mdd < e[0]][0]
    except:
        return 0


def get_western_zodiac(dob):
    try:
        return WESTERN_ZODIAC[get_western_zodiac_index(dob)][1]
    except IndexError:
        return ''


def get_western_zodiac_symbol(dob):
    try:
        return WESTERN_ZODIAC_SYMBOLS[get_western_zodiac_index(dob)][1]
    except IndexError:
        return ''


def get_eastern_zodiac_index(dob):
    """Gets a datetime.date value and returns its Eastern zodiac"""
    try:
        ymd = int(dob.strftime('%Y%m%d'))
        lim = EASTERN_ZODIAC_UPPER_LIMIT
        return [e[1] for e in lim if ymd < e[0]][0]
    except:
        return 0


def get_eastern_zodiac(dob):
    try:
        return EASTERN_ZODIAC[get_eastern_zodiac_index(dob)][1]
    except IndexError:
        return ''


def get_eastern_zodiac_symbol(dob):
    try:
        return EASTERN_ZODIAC_SYMBOLS[get_eastern_zodiac_index(dob)][1]
    except IndexError:
        return ''


# --- Geolocation --------------------------------------------------- #


def distance_between_geolocations(p1, p2):
    """
    Gets two geolocation points p1 and p2 as (lat, lng) tuples. Returns
    the approximate distance in meters. Does not account for earth's
    curvature, so that inaccurency increases with distance.
    """
    p1_lat, p1_lng = float(p1[0]), float(p1[1])
    p2_lat, p2_lng = float(p2[0]), float(p2[1])
    lat_1_deg = 110574.0  # 1 deg lat in meters (m)
    p1_lng_1_deg = 111320.0 * math.cos(p1_lat)  # 1 deg lng in m for p1_lat
    p2_lng_1_deg = 111320.0 * math.cos(p2_lat)  # 1 deg lng in m for p2_lat
    lng_1_deg = (p1_lng_1_deg + p2_lng_1_deg) / 2  # average them
    lat_delta_m = (p1_lat - p2_lat) * lat_1_deg
    lng_delta_m = (p1_lng - p2_lng) * lng_1_deg
    return int(math.sqrt(math.pow(lat_delta_m, 2) + math.pow(lng_delta_m, 2)))


def get_latlng_bounderies(lat, lng, distance):
    """Return min/max lat/lng values for a distance around a latlng.

    Receives a geolocation as lat/lng floats and a distance (km) around
    that point. To simplify database lookup, only get a square around
    the geolocation. Return (lat_min, lng_min) and (lat_max, lng_max)
    geolocation points to draw the box.
    """
    lat_1deg = 110574.0  # m
    lng_1deg = 111320.0 * math.cos(lat)  # m
    dist_m = float(distance * 1000)
    lat_dist_deg = abs(dist_m / lat_1deg)
    lng_dist_deg = abs(dist_m / lng_1deg)
    return (lat-lat_dist_deg, lng-lat_dist_deg,
            lat+lng_dist_deg, lng+lng_dist_deg)


# ------------------------------------------------------------------- #
