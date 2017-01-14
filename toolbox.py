"""
Collection of random simple general-purpose helper functions.
"""

import math
from datetime import date, datetime

import dateutil.parser
import pytz
import re
from geopy.distance import great_circle


def meters_in_km(m):
    """Return the given meters in km."""
    return float(m / 1000)


def meters_in_miles(m):
    """Return the given meters in miles."""
    return float(meters_in_km(m) * 0.621371)


def sr_str_to_list(s):
    """
    Receive a string that contains a list of subreddit names, separated
    by comma or spaces or similar characters. Split the string into a list
    of clean subreddit names and return the list.
    """
    if not s:
        return []
    li = re.split('[^A-Za-z0-9_-]+', s)
    li = [x for x in li]  # TODO: clean up, especially any leading "_".
    return li


def get_age(dob):
    delta = date.today() - dob
    return int(float(delta.days) / 365.25)


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


# noinspection PyShadowingBuiltins
def force_int(x, min=None, max=None):
    """
    Receives any value and returns an integer. Values that can not be
    parsed are returned as 0. Values that are smaller that min or
    larger than max, if either is given, are set to min or max
    respectively.
    """
    if isinstance(x, str):
        x = x.replace(',', '')  # remove any "," separators
    if x:
        try:
            i = int(x)
        except ValueError:
            i = 0
    else:
        i = 0
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
    # noinspection PyBroadException
    try:
        return float(x)
    except:
        return 0


# --- Date of Birth and Zodiac -------------------------------------- #


def get_dob_range(minage, maxage):
    """Return earliest and latest dob to match a min/max age range."""
    year = date.today().year
    today = date.today()
    # This will fail with a ValueError "day is out of range for month" on
    # February 29, every four years.
    if today.month == 2 and today.day == 29:
        today = date(today.year, 2, 28)  # good enough for the purpose.
    dob_earliest = today.replace(year=(year-maxage))
    dob_latest = today.replace(year=(year-minage))
    return dob_earliest, dob_latest


WESTERN_ZODIAC = (
    (0, ''),
    (1, 'aries'), (2, 'taurus'), (3, 'gemini'), (4, 'cancer'), (5, 'leo'),
    (6, 'virgo'), (7, 'libra'), (8, 'scorpio'), (9, 'sagittarius'),
    (10, 'capricorn'), (11, 'aquarius'), (12, 'pisces'))

WESTERN_ZODIAC_SYMBOLS = (
    (0, ''),
    (1, '♈'), (2, '♉'), (3, '♊'), (4,  '♋'), (5,  '♌'), (6,  '♍'),
    (7, '♎'), (8, '♏'), (9, '♐'), (10, '♑'), (11, '♒'), (12, '♓'))

WESTERN_ZODIAC_UPPER_LIMIT = (
    (120, 10), (218, 11), (320, 12), (420, 1), (521, 2), (621, 3), (722, 4),
    (823, 5), (923, 6), (1023, 7), (1122, 8), (1222, 9), (1231, 10))

EASTERN_ZODIAC = (
    (0, ''),
    (1, 'rat'), (2, 'ox'), (3, 'tiger'), (4, 'rabbit'),
    (5, 'dragon'), (6, 'snake'), (7, 'horse'), (8, 'goat'),
    (9, 'monkey'), (10, 'rooster'), (11, 'dog'), (12, 'pig'))

EASTERN_ZODIAC_SYMBOLS = (
    (0, ''),
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
    # noinspection PyBroadException
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
    # noinspection PyBroadException
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
    the approximate distance in meters.
    """
    lat1, lng1 = float(p1[0]), float(p1[1])
    lat2, lng2 = float(p2[0]), float(p2[1])

    # Fast Haversine http://stackoverflow.com/a/21623206/101801 and
    # https://github.com/geopy/geopy/blob/1.11.0/geopy/distance.py#L237
    p = 0.017453292519943295  # math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p)/2 +
         math.cos(lat1 * p) *
         math.cos(lat2 * p) *
         (1 - math.cos((lng2 - lng1) * p)) / 2)
    return 12742000 * math.asin(math.sqrt(a))  # 12742000 == 2 * Earth radius


def get_latlng_bounderies(lat, lng, distance):
    """
    Return min/max lat/lng values for a distance around a latlng.

    :lat:, :lng: the center of the area.
    :distance: in km, the "radius" around the center point.

    :returns: Two corner points of a square that countains the circle,
              lat_min, lng_min, lat_max, lng_max.
    """
    gc = great_circle(kilometers=distance)
    p0 = gc.destination((lat, lng), 0)
    p90 = gc.destination((lat, lng), 90)
    p180 = gc.destination((lat, lng), 180)
    p270 = gc.destination((lat, lng), 270)

    ret = p180[0], p270[1], p0[0], p90[1]
    print(ret)
    return ret

# ------------------------------------------------------------------- #
