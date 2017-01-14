import re
import requests


# E.g. http://imgur.com/a/Sxk3RM2
re_album = re.compile(r'imgur\.com/a/[a-z0-9]{4,9}(/new)?$',
                      flags=re.IGNORECASE)

# E.g. http://m.imgur.com/gallery/qXcqEM9
#      http://imgur.com/gallery/rgMhYjO/new
re_gallery = re.compile(r'imgur.com/gallery/[a-z0-9]{4,9}(/new)?$',
                        flags=re.IGNORECASE)

# E.g. http://m.imgur.com/dmkK3M2  Http://imgur.com/gF245
re_noext = re.compile(r'imgur.com/[a-z0-9]{4,9}$',
                      flags=re.IGNORECASE)

# E.g. http://imgur.com/r/IASIP/S0kKRM2
re_srpic = re.compile(r'imgur.com/r/[a-z0-9_-]+/[a-z0-9]{4,9}$',
                      flags=re.IGNORECASE)

# E.g. http://imgur.com/topic/Caturday/b1LXq
#      https://imgur.com/t/golden_retriever/XYyQ1R1
#      http://imgur.com/t/tyler_durden/tGNRnFp
re_topic = re.compile(r'imgur.com/t(opic)?/[a-z0-9_-]+/[a-z0-9]{4,9}$',
                      flags=re.IGNORECASE)

# These usually return HTTP 403
# E.g. https://scontent.xx.fbcdn.net/v/t1.0-9/133...958_n.jpg?oh=bb1...0dd
re_fbcdn = re.compile(r'\.fbcdn\.net/')

# Extract main picture URL from album / gallery / topic page.
re_imgsrc = re.compile(r'<link\s+rel="image_src"\s+href="(?P<pic>.+?)"\s*/?>')

# Extract main picture URL from video pages (mp4, gifv)
re_vidsrc = re.compile(
    r'<meta\s+itemprop="thumbnailUrl"\s+content="(?P<src>.+?h\.jpg)"\s+/>')


def extract_image_src(url, size):
    # Find this line and extract the image, for example:
    # <link rel="image_src"   href="http://i.imgur.com/hOexIku.jpg"/>
    r = requests.get(url)
    if r.status_code != 200:
        return ''  # Empty URL
    m = re_imgsrc.search(r.text)

    try:
        url = m.group('pic')
        url = url.replace('.jpg', '{}.jpg'.format(size))
    except AttributeError:
        url = maybe_video_src(r.text, size)

    return url


def maybe_video_src(text, size):
    m = re_vidsrc.search(text)

    # Returns a URL like this https://i.imgur.com/tGNRnFph.jpg
    # The "h.jpg" means this is a static image for the video. To get the
    # medium size, replace "h" with "m" as usual.
    try:
        url = m.group('src')
        url = url.replace('h.jpg', '{}.jpg'.format(size))
    except AttributeError:
        url = ''

    return url


def set_imgur_url(url="http://i.imgur.com/wPqDiEy.jpg", size='t'):
    """
    Fallback for any other URL format.

    Convert a variety of Imgur links into a direct link to the picture.

    :url: the URL with the full size image ID on Imgur, with no size Bytes.

    Examples:

        https://i.imgur.com/kMoI9Vn.jpg -- full size picture
        https://i.imgur.com/f7VXJQF -- same but missng ext.
        https://imgur.com/S1dZBPm --  picture page
        https://imgur.com/gallery/HFoOCeg -- gallery link (don't always work)
        http://m.imgur.com/182moWW -- mobile picture page
        http://imgur.com/a/bhRB6
        ...and more

    :size: the required picture "size" Byte:
        See: http://api.imgur.com/models/image

        s = Small Square (90x90)
        b = Big Square (160x160)
        t = Small Thumbnail (160x160)
        m = Medium Thumbnail (320x320)
        l = Large Thumbnail (640x640)
        h = Huge Thumbnail (1024x1024)
          = original upload size

    If :url: is not a valid Imgur URL, the value is returned unchanged.
    """
    base = 'https://i.imgur.com/'

    if re_album.search(url):
        url = extract_image_src(url, size)
    elif re_gallery.search(url):
        url = extract_image_src(url, size)
    elif re_topic.search(url):
        url = extract_image_src(url, size)
    elif re_noext.search(url):
        partial = url.rsplit('/', 1)[1]
        url = '{}{}{}.jpg'.format(base, partial, size)
    elif re_srpic.search(url):
        partial = url.rsplit('/', 1)[1]
        url = '{}{}{}.jpg'.format(base, partial, size)
    else:
        m = re.search(r'^https?://(?:[im].)?imgur.com/(?:gallery/)?'
                      r'(?P<name>[a-zA-Z0-9]{5,20})'
                      r'(?P<ext>\.[a-zA-Z]{3,4})?$', url)
        if m:
            ext = m.group('ext') or '.jpg'
            url = '{}{}{}{}'.format(base, m.group('name'), size, ext)

    return url


def get_imgur_page_from_picture_url(url):
    """
    Returns the URL of the containing page for a picture URL
    on imgur.com
    """
    m = re.search(r'^https?://i.imgur.com/(?P<name>[a-zA-Z0-9]{2,20})'
                  r'[stml]?\.(?P<ext>jpe?g|gif|png|webp)$', url)
    if m:
        return 'https://imgur.com/{}'.format(m.group('name'))
    else:
        return ''
