import os
import re
import logging

DEBUG = bool(os.environ.get("ISDEV"))

logger = logging.getLogger(__name__)
logger.info("DEBUG: %s", DEBUG)

if DEBUG:
    logger.info("Using development settings...")
    from .settings_development_private import *
else:
    logger.info("Using production settings...")
    from .settings_production_private import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if DEBUG:
    ALLOWED_HOSTS = ["localhost"]
    CANONICAL_HOST = "http://localhost:8000"
else:
    ALLOWED_HOSTS = ["redddate.com", "reddmeet.com"]
    CANONICAL_HOST = "https://reddmeet.com"

LOGIN_URL = "/"

AUTHENTICATION_BACKENDS = ("simple_reddit_oauth.backends.RedditBackend",)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5433"),
        "NAME": os.environ.get("POSTGRES_NAME", "dtr5"),
        "USER": os.environ.get("POSTGRES_USER", "dev"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "12345678"),
        #"POOL_OPTIONS": {
        #    'POOL_SIZE': 10,
        #    'MAX_OVERFLOW': 10,
        #},
        #"OPTIONS": {
        #    "keepalives": 1,
        #    "keepalives_idle": 30,
        #    "keepalives_interval": 10,
        #    "keepalives_count": 5,
        #},
    },
}

print("######## Connecting to DB: %s", DATABASES)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s:%s/1" % (os.environ.get("REDIS_HOST", "localhost"), os.environ.get("REDIS_PORT", "6379")),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",},
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "corsheaders",
    "rest_framework",
    "simple_reddit_oauth",
    "dtr5app",
)

MIDDLEWARE = (
    # 'dtr5app.middleware.CheckSiteTemporarilyUnavailable',
    # 'dtr5app.middleware.CheckSiteUnavailableIfSiteIsOnlineNotFound',
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'dtr5app.middleware.UserSetDefaultLocalizationValues',
    # 'dtr5app.middleware.UserProfileLastActiveMiddleware',
)

ROOT_URLCONF = "dtr5.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dtr5app.context_processors.selected_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "dtr5.wsgi.application"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False  # english only, for now
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# =====================================
# settings for "django-cors-headers"
# =====================================

# https://github.com/ottoyiu/django-cors-headers
# CORS_ORIGIN_ALLOW_ALL = True
# CORS_ORIGIN_WHITELIST = ['localhost:3333', 'localhost:8000']

# =====================================

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    )
}

# =====================================
# settings for "dtr5app"
# =====================================

# block signups, logins, or all access.
ALLOW_USER_SIGNUP = True  # new users can register               # unused
ALLOW_USER_LOGIN = True  # existing users can login              # unused

# Content types for user profile pictures
PIC_CONTENT_TYPES = ["image/jpeg", "image/gif", "image/webp", "image/png"]

# turn OFF entire site. WARNING: there is another switch to turn off the
# site via the dtr5app.middleware.MakeSiteUnavailable()
SITE_TEMPORARILY_UNAVAILABLE = False

# minimum limits for new users: must be older that X days AND have
# either Y link or Z comment karma.
USER_MIN_SUBSCRIBED_SUBREDDITS = 10  # show warning only if less subs
USER_MIN_DAYS_REDDIT_ACCOUNT_AGE = 0  # days of being a reddit member
USER_MIN_LINK_KARMA = 0  # AND either xy link karma
USER_MIN_COMMENT_KARMA = 0  # OR xy comment karma.

# Number of user IDs to load into session cache.
SEARCH_RESULTS_BUFFER_SIZE = 100  # unused?

LINKS_IN_PROFILE_HEADER = 5
RESULTS_BUFFER_TIMEOUT = 10  # minutes until search result cache refresh
RESULTS_BUFFER_LEN = 1000  # usernames in search result cache
USER_MAX_PICS_COUNT = 10  # max number of linked pics in user profile

# Ignore subreddits too small or too large.
SR_MIN_SUBS = 10  # unused
SR_MAX_SUBS = 5000000  # unused

# How many subreddits to use at a time to find matches.
SR_LIMIT = 50

# How many favorite subreddits can a user select.
SR_FAVS_COUNT_MAX = 10

# How many users to show per page (subreddit view, match view, likes view, ..)
USERS_PER_PAGE = 20
USERS_ORPHANS = 0

# Limit number of subreddits to fetch
SR_FETCH_LIMIT = 200  # None to fetch all

# Use this to only show profiles with pic in search results
REQUIRE_PROFILE_PIC = False  # partially implemented

# Strings for common regular expressions: username, subreddit, etc.
#
# https://github.com/reddit/reddit/blob/master/r2/r2/models/subreddit.py#L111
#
# -> subreddit_rx = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_]{2,20}\Z")
# -> language_subreddit_rx = re.compile(r"\A[a-z]{2}\Z")
# -> time_subreddit_rx = re.compile(r"\At:[A-Za-z0-9][A-Za-z0-9_]{2,22}\Z")
#
# Careful, there is also "r/reddit.com" as a subreddit, that contains a "."
# even though there is no "." in any of the above regexes. Surprise!
#
RSTR_SR_NAME = r"[a-zA-Z0-9:._-]{2,30}"
RSTR_USERNAME = r"[a-zA-Z0-9_-]{2,30}"

RE_USERNAME = re.compile(RSTR_USERNAME)

# first try user pref, then try user browser ll setting, then this.
DEFAULT_DISTANCE_UNIT = "mi"

# Public settings for Reddit oAuth access.
OAUTH_REDDIT_REDIRECT_URI = CANONICAL_HOST + "/account/redditcallback/"
OAUTH_REDDIT_REDIRECT_AUTH_SUCCESS = CANONICAL_HOST + "/me/"
OAUTH_REDDIT_REDIRECT_AUTH_ERROR = LOGIN_URL

# Comma-separated list of API access scope with any of:
# identity edit flair history modconfig modflair modlog
# modposts modwiki mysubreddits privatemessages read report
# save submit subscribe vote wikiedit wikiread
OAUTH_REDDIT_SCOPE = "identity,mysubreddits"
OAUTH_REDDIT_DURATION = "permanent"  # or "temporary"
OAUTH_REDDIT_BASE_HEADERS = {
    "User-Agent": OAUTH_REDDIT_USER_AGENT,
    "raw_json": "1",
}

# List some subreddits where anonymous users are allowed to view user list of
# subreddit subscribers.
SR_ANON_ACCESS_ALLOWED = (
    "bestof",
    "CrappyDesign",
    "ProgrammerHumor",
    "announcements",
    "Art",
    "AskReddit",
    "askscience",
    "aww",
    "blog",
    "books",
    "creepy",
    "dataisbeautiful",
    "DIY",
    "Documentaries",
    "EarthPorn",
    "explainlikeimfive",
    "Fitness",
    "food",
    "funny",
    "Futurology",
    "gadgets",
    "gaming",
    "GetMotivated",
    "gifs",
    "history",
    "IAmA",
    "InternetIsBeautiful",
    "Jokes",
    "LifeProTips",
    "listentothis",
    "mildlyinteresting",
    "movies",
    "Music",
    "news",
    "nosleep",
    "nottheonion",
    "OldSchoolCool",
    "personalfinance",
    "philosophy",
    "photoshopbattles",
    "pics",
    "science",
    "Showerthoughts",
    "space",
    "sports",
    "television",
    "tifu",
    "todayilearned",
    "TwoXChromosomes",
    "UpliftingNews",
    "videos",
    "worldnews",
    "WritingPrompts",
)

# Settings for user profile data.
SEX = (
    (0, "other"),
    (1, "woman who likes men"),
    (2, "woman who likes women"),
    (3, "woman who likes diverse"),
    (4, "man who likes women"),
    (5, "man who likes men"),
    (6, "man who likes diverse"),
    (7, "diverse who likes women"),
    (8, "diverse who likes men"),
    (9, "diverse who likes diverse"),
)
SEX_PLURAL = (
    (0, "other"),
    (1, "women who like men"),
    (2, "women who like women"),
    (3, "women who like diverse"),
    (4, "men who like women"),
    (5, "men who like men"),
    (6, "men who like diverse"),
    (7, "diverse who like women"),
    (8, "diverse who like men"),
    (9, "diverse who like diverse"),
)
SEX_SYMBOL = (  # ♀♂⚥⚢⚣⚤⚪★☆⮕♥
    (0, "⚪"),
    (1, "♀♥♂"),
    (2, "♀♥♀"),
    (3, "♀♥⚥"),
    (4, "♂♥♀"),
    (5, "♂♥♂"),
    (6, "♂♥⚥"),
    (7, "⚥♥♀"),
    (8, "⚥♥♂"),
    (9, "⚥♥⚥"),
)
LOOKINGFOR = (
    (1, "someone to chat"),
    (17, "penpals"),
    (2, "hugs and nice words"),
    (3, "new friends"),
    (4, "sexy time"),
    (5, "dating"),
    (6, "serious dating"),
    (7, "a relationship"),
    (8, "marriage"),
    (9, "house+car+kids... now!"),
    (10, "just another cat"),
    (11, "my car keys"),
    (12, "world peace"),
    (13, "the grand unified theory"),
    (14, "this is getting ridiculous"),
    (15, "stahp!"),
    (16, "just some nice person, really"),
)

# Below are bitmaps for future-proof...

RELSTATUS = (  # unused
    (1, "don't know"),
    (2, "single"),
    (4, "seeing someone"),
    (8, "in a relationship"),
    (16, "in an open relationship"),
    (32, "married"),
)
EDUCATION = (  # unused
    (1, "yes"),
    (2, "no"),
    (4, "other"),
    (8, "trade school"),
    (16, "high school"),
    (32, "university"),
    (64, "masters degree"),
    (128, "PhD, MD, etc."),
    (256, "self-taught"),
)
FITNESS = (  # unused
    (1, "don't know"),
    (2, "not really"),
    (4, "somewhat"),
    (8, "yes"),
    (16, "very"),
    (32, "a lot"),
)
# REPORT_REASON_CHOICES = ()

DISTANCE = (
    (1, "worldwide"),  # any value below 5 will be used for "worldwide"...
    (5000, "5000 km / 3100 miles"),  # ...don't set 0 because it would be ...
    (2000, "2000 km / 1250 miles"),  # ...intercepted by the signup flow.
    (1000, "1000 km / 620 miles"),
    (700, "700 km / 435 miles"),
    (500, "500 km / 310 miles"),
    (300, "300 km / 186 miles"),
    (200, "200 km / 125 miles"),
    (100, "100 km / 62 miles"),
    (50, "50 km / 31 miles"),
    (20, "20 km / 12 miles"),
)

HEREFOR_ONLY_DATING = 1
HEREFOR_MOSTLY_DATING = 2
HEREFOR_FRIENDS_OR_DATING = 4
HEREFOR_MOSTLY_FRIENDS = 8
HEREFOR_ONLY_FRIENDS = 16
HEREFOR = (
    (HEREFOR_ONLY_DATING, "only dating"),
    (HEREFOR_MOSTLY_DATING, "mostly dating"),
    (HEREFOR_FRIENDS_OR_DATING, "friends or dating"),
    (HEREFOR_MOSTLY_FRIENDS, "mostly friends"),
    (HEREFOR_ONLY_FRIENDS, "only friends"),
)

GENDER = (  # bitmap  # unused
    (1, "don't know"),
    (2, ""),
    (4, ""),
    (8, ""),
    (16, ""),
    (32, ""),
    (64, ""),
    (128, ""),
    (256, ""),
    (512, ""),
    (1024, ""),
)

PREFERENCE = (  # bitmap  # unused
    (1, "don't know"),
    (2, ""),
    (4, ""),
    (8, ""),
    (16, ""),
    (32, ""),
    (64, ""),
    (128, ""),
    (256, ""),
    (512, ""),
    (1024, ""),
    (2048, ""),
    (4096, ""),
    (8192, ""),
    (16384, ""),
    (32768, ""),
    (65536, ""),
)

ORDER_BY = (
    ("-sr_count", "best matches"),
    ("-accessed", "recently active"),
    # ('reddit_joined', 'reddit oldest'), --> no, b/c "created" data bug.
    ("-date_joined", "newest members"),
    ("-views_count", "most viewed"),
    # ('accessed', ''),
    # ('date_joined', ''),
    # ('views_count', ''),
)
