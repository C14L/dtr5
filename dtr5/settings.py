"""
Django settings for dtr5 project.

Generated by 'django-admin startproject' using Django 1.8.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
DEBUG = os.path.exists('/islocal.txt')
print('--> DEBUG: {}'.format(DEBUG))

# Import the following "secret" settings
SECRET_KEY = ''
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    'HOST': 'localhost', 'NAME': '', 'USER': '', 'PASSWORD': '', }}
OAUTH_REDDIT_CLIENT_ID = ''
OAUTH_REDDIT_CLIENT_SECRET = ''
OAUTH_REDDIT_USER_AGENT = ''
#######################################
from .settings_secrets import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if DEBUG:
    ALLOWED_HOSTS = ['localhost']
    CANONICAL_HOST = 'http://localhost:8000'
else:
    ALLOWED_HOSTS = ['redddate.com']
    CANONICAL_HOST = 'http://redddate.com'

LOGIN_URL = CANONICAL_HOST + '/'

AUTHENTICATION_BACKENDS = (
    # 'django.contrib.auth.backends.ModelBackend',  # default
    # 'django.contrib.auth.backends.RemoteUserBackend',
    'simple_reddit_oauth.backends.RedditBackend',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'simple_reddit_oauth',
    'dtr5app',
)

MIDDLEWARE_CLASSES = (
    'dtr5app.middleware.CheckSiteTemporarilyUnavailable',
    'dtr5app.middleware.CheckSiteUnavailableIfSiteIsOnlineNotFound',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'dtr5app.middleware.UserProfileLastActiveMiddleware',
)

ROOT_URLCONF = 'dtr5.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dtr5app.context_processors.selected_settings',
                'dtr5app.context_processors.site_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'dtr5.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False  # english only, for now
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static')

# all logging to console, incl. logleves INFO and DEBUG, when DEBUG is True
# See https://docs.djangoproject.com/en/1.8/topics/logging/
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

# =====================================
# settings for "dtr5app"
# =====================================

# block signups, logins, or all access.
ALLOW_USER_SIGNUP = True  # new users can register               # unused
ALLOW_USER_LOGIN = True  # existing users can login              # unused

# turn OFF entire site. WARNING: there is another switch to turn off the
# site via the dtr5app.middleware.MakeSiteUnavailable()
SITE_TEMPORARILY_UNAVAILABLE = False

# minimum limits for new users: must be older that X days AND have
# either Y link or Z comment karma.
USER_MIN_SUBSCRIBED_SUBREDDITS = 10    # show warning only if less subs
USER_MIN_DAYS_REDDIT_ACCOUNT_AGE = 0  # days of being a reddit member
USER_MIN_LINK_KARMA = 0              # AND either xy link karma
USER_MIN_COMMENT_KARMA = 0           # OR xy comment karma.

# Number of user IDs to load into session cache.
SEARCH_RESULTS_BUFFER_SIZE = 100
LINKS_IN_PROFILE_HEADER = 5
RESULTS_BUFFER_LEN = 20 if DEBUG else 500
USER_MAX_PICS_COUNT = 10  # max number of linked pics in user profile

# Ignore subreddits too small or too large.
SR_MIN_SUBS = 10
SR_MAX_SUBS = 5000000

# How many subreddits to use at a time to find matches.
SR_LIMIT = 50

# How many favorite subreddits can a user select.
SR_FAVS_COUNT_MAX = 10

# How many subreddit users to show per page in subreddit view
SR_USERS_PER_PAGE = 20

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
    "User-Agent": OAUTH_REDDIT_USER_AGENT, "raw_json": "1", }

# Settings for user profile data.
SEX = (
    (0, 'other'),
    (1, 'woman who likes men'),
    (2, 'woman who likes women'),
    (3, 'woman who likes queer'),
    (4, 'man who likes women'),
    (5, 'man who likes men'),
    (6, 'man who likes queer'),
    (7, 'queer who likes women'),
    (8, 'queer who likes men'),
    (9, 'queer who likes queer'),
)
SEX_SYMBOL = (  # ♀♂⚥⚢⚣⚤⚪★☆⮕♥
    (0, '⚪'),
    (1, '♀♥♂'),
    (2, '♀♥♀'),
    (3, '♀♥⚥'),
    (4, '♂♥♀'),
    (5, '♂♥♂'),
    (6, '♂♥⚥'),
    (7, '⚥♥♀'),
    (8, '⚥♥♂'),
    (9, '⚥♥⚥'),
)
LOOKINGFOR = (
    (1, 'someone to chat'),
    (2, 'hugs and nice words'),
    (3, 'new friends'),
    (4, 'sexy time'),
    (5, 'dating'),
    (6, 'serious dating'),
    (7, 'a relationship'),
    (8, 'marriage'),
    (9, 'house+car+kids... now!'),
    (10, 'just another cat'),
    (11, 'my car keys'),
    (12, 'world peace'),
    (13, 'the grand unified theory'),
    (14, 'this is getting ridiculous'),
    (15, 'stahp!'),
    (16, 'just some nice person, really'),
)
RELSTATUS = (  # unused
    (2, 'single'),
    (4, 'seeing someone'),
    (6, 'in a relationship'),
    (8, 'open relationship'),
    (10, 'married'),
)
EDUCATION = (  # unused
    (2, 'high school'),
    (4, 'trade school'),
    (6, 'university'),
    (8, 'masters degree'),
    (10, 'PhD, MD, etc.'),
    (12, 'yes'),
    (14, 'no'),
)
FITNESS = (  # unused
    (1, 'not really'),
    (2, 'somewhat'),
    (3, 'yes'),
    (4, 'very'),
    (5, 'even more'),
)
# REPORT_REASON_CHOICES = ()
