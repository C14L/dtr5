"""
Helper functions to download user pics from web sources and convert them to
standard sizes (/s/=100x100 and /m/=600x600) and file format (jpg).
"""
import os
from django.contrib.auth.models import User
from os.path import isfile, join, getsize
from PIL import Image, ImageFont, ImageDraw


jpeg_quality = 75
watermark_text = 'Meet Redditors: reddmeet.com'
watermark_font = '/usr/share/fonts/truetype/freefont/FreeSans.ttf'
watermark_fontsize = 13


def check_raw_files_have_active_user(base_dir, raw_dir, sizes):
    """
    Make sure that for every file in /raw/ there is an existing and
    active user in the database. Files in /raw/ that are not associated
    to an active user account must be deleted.
    """
    deleted, total = 0, 0
    filenames = [f for f in os.listdir(raw_dir) if isfile(join(raw_dir, f))]
    users = User.objects.filter(is_active=True)\
                        .filter(last_login__isnull=False)\
                        .exclude(profile___pics='')\
                        .order_by('date_joined')

    for filename in filenames:
        username = filename[:filename.rindex('.')]
        total += 1

        try:
            users.get(username=username)
        except users.DoesNotExist:
            print('No user found for {}'.format(filename), end=' ', flush=True)
            os.remove(join(raw_dir, filename))
            deleted += 1
            print('deleted.', flush=True)

    print('Done checking raw files for active database user.')
    print('{} files checked, and {} deleted.'.format(total, deleted))


def check_public_files_all_have_a_raw_file(base_dir, raw_dir, sizes):
    """
    Make sure that there are no public files in either /s/ or /m/ that don't
    have a source image file in /raw/. Any files in /s/ and /m/ without a
    source file in /raw/ must be deleted.
    """
    for n in sizes.keys():
        ndir = join(base_dir, n)
        for filename in [f for f in os.listdir(ndir) if isfile(join(ndir, f))]:
            file = join(raw_dir, filename)
            if isfile(file) and getsize(file) > 1023:
                print('.', end='', flush=True)
            else:
                print('x', end='', flush=True)
                os.remove(join(ndir, filename))

    print('Done checking public files for existing raw file.')


def create_public_pics_for_every_raw_file(base_dir, raw_dir, sizes):
    """
    Make sure that for every source image file in /raw/ there are public
    files in /s/ and /m/. Create them if necessary.
    """
    i, j = 0, 0
    for fname in [f for f in os.listdir(raw_dir) if isfile(join(raw_dir, f))]:
        rawfile = join(raw_dir, fname)

        if getsize(rawfile) < 1024:
            print('Skip empty raw file: {}'.format(rawfile))
            continue

        for n in sizes.keys():
            nfile = join(base_dir, n, fname)
            w, h = sizes[n].split('x', 1)

            if isfile(nfile):  # target size file already exists, skip
                continue

            try:
                r = resize_copy(rawfile, nfile, 'cover', int(w), int(h), True)
            except OSError:
                r = False

            if r:
                i += 1
                print('{} -({})-> {}'.format(rawfile, sizes[n], nfile))
            else:
                print('ERROR creating {}'.format(nfile))

    print('Done creating {} public files.'.format(i))


def resize_copy(raw_fname: str, target_fname: str, resize_type: str,
                max_w: int, max_h: int, watermark: bool=False) -> bool:
    """
    Make a resized JPEG copy of the image with file name "raw_fname" and write
    the resulting image data to a file named "target_fname".

    The resulting image will be not larger than "max_w x max_h" pixels and is
    resized to either "contain" the original image completely and have some
    empty areas on the target image, or to "cover" the target image completely
    by cropping parts of the original image.

    :param raw_fname: Full file name of raw image.
    :param target_fname: Full file name of target image.
    :param resize_type: Either "cover" or "contain", like CSS3.
    :param max_w: Maximum width of target image.
    :param max_h: Maximum height of target image.
    :param watermark: Optional. If True, add settings.SITE_NAME as watermark.
    """
    file_type = 'JPEG'
    # raw_fh.seek(0)
    im = Image.open(raw_fname).convert('RGBA')

    # Original image size.
    curr_w, curr_h = im.size

    # Resize either "cover" or "contain".
    if resize_type == 'cover':
        # Same as CSS3, cover the entire target image and crop
        w = int(max_w)
        h = int(max(curr_h * max_w / curr_w, 1))
        cx2, cy2 = 0, int((h - max_h) / 2)  # part to crop
        if h < max_h:
            h = int(max_h)
            w = int(max(curr_w * max_h / curr_h, 1))
            cx2, cy2 = int((w - max_w) / 2), 0  # part to crop
        im = im.resize((w, h), Image.ANTIALIAS).crop((cx2, cy2, w-cx2, h-cy2))
        im.load()  # load() is necessary after crop

    elif resize_type == 'contain':
        # First calc to fit the width. Then check to see if height is still
        # too large, and if so, calc again to fit height.
        #
        # max_w, max_h: this is the target.
        # curr_w, curr_h: this is the current situation.
        if curr_w > max_w:
            curr_h = int(max(curr_h * max_w / curr_w, 1))
            curr_w = int(max_w)
        if curr_h > max_h:
            curr_w = int(max(curr_w * max_h / curr_h, 1))
            curr_h = int(max_h)
        im = im.resize((curr_w, curr_h), Image.ANTIALIAS)

    else:
        raise ValueError('No such resize_type "{}".'.format(resize_type))

    is_w, is_h = im.size
    if watermark and is_w > 300:
        txt = watermark_text
        font = ImageFont.truetype(watermark_font, watermark_fontsize)
        im_tx_dark = Image.new('RGBA', im.size, (32, 32, 32, 0))
        im_tx_light = Image.new('RGBA', im.size, (255, 255, 255, 0))
        draw_ctx_dark = ImageDraw.Draw(im_tx_dark)
        draw_ctx_light = ImageDraw.Draw(im_tx_light)
        pos_light = (10, is_h-watermark_fontsize-10)
        pos_dark = (pos_light[0]+2, pos_light[1]+2)
        draw_ctx_dark.text(pos_dark, txt, font=font, fill=(32, 32, 32, 192))
        draw_ctx_light.text(pos_light, txt, font=font, fill=(255, 255, 255, 192))
        im = Image.alpha_composite(im, im_tx_dark)
        im = Image.alpha_composite(im, im_tx_light)

    im.save(target_fname, file_type)
    return True
