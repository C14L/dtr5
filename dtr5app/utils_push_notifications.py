import json
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now
from pywebpush import WebPusher, WebPushException


def simple_push_notification(sender, receiver, notiftype, teaser=''):
    """
    Send a Push Notification to all registered endpoints of user 'receiver'.
    """
    data = {}
    ttl = 120
    gcm_url = 'https://android.googleapis.com/gcm/send'
    endpoints = receiver.endpoints.all()

    if settings.DEBUG:
        print('- ' * 30)
        print('# simple_push_notification() with:')
        print('#     sender: {}'.format(sender))
        print('#   receiver: {}'.format(receiver))
        print('#  notiftype: {}'.format(notiftype))
        print('#     teaser: {}'.format(teaser))
        print('#  endpoints: {}'.format(endpoints.count()))

    for obj in endpoints:
        # Special case Google: needs gcm_key as API key.
        gcm_key = settings.GCM_AUTHKEY if gcm_url in obj.sub else None

        # Make sure we only send one per minute at most. Further limit it on
        # the client device.
        if (obj.latest + timedelta(minutes=1)) > now():
            return False
        obj.latest = now()
        obj.save()

        if settings.DEBUG:
            print('- ' * 30)
            print('#    obj.sub: {}'.format(obj.sub))

        subscription_info = json.loads(obj.sub)

        if settings.DEBUG:
            print('# sub...info: {}'.format(subscription_info))

        headers = {'Content-Type': 'application/json'}
        data['notiftype'] = notiftype  # 'message', 'upvote', etc.
        data['username'] = sender.username  # Sender's username.
        data['teaser'] = teaser  # A few words of a message received, if any.
        data_str = json.dumps(data, ensure_ascii=True)

        if settings.DEBUG:
            print('#   data_str: {}'.format(data_str))

        try:
            WebPusher(subscription_info).send(data_str, headers, ttl, gcm_key)
        except WebPushException as e:
            # "subscription_info missing keys dictionary"
            if settings.DEBUG:
                print('WebPushException: {}'.format(e))
