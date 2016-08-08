import json

from channels import Channel, Group
from channels.auth import channel_session_user, channel_session_user_from_http
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from dtr5app.models import Message


def get_group_id_for_user(user):
    return 'user-{}'.format(user.id)


@channel_session_user
def message_consumer(message):
    payload = json.loads(message.content['text'])
    msg = payload['msg']
    sender = message.user
    receiver = get_object_or_404(User, username=payload['receiver'])
    sender_group = get_group_id_for_user(sender)
    receiver_group = get_group_id_for_user(receiver)

    print('### message_consumer: sender_group == "{}"'.format(sender_group))
    print('### message_consumer: receiver_group == "{}"'.format(receiver_group))
    print('### message consumer: msg == {}'.format(msg))
    print('### message consumer: message.content == {}'.format(message.content))
    print('### message consumer: message.channel == {}'.format(message.channel))

    m = Message.objects.create(msg=msg, sender=sender, receiver=receiver)
    resp = [{
        'action': 'chat.receive',
        'id': m.id,
        'msg': m.msg,
        'sender': m.sender.username,
        'receiver': m.receiver.username,
        'created': str(m.created)[:19],  # e.g. '2016-08-08 13:50:38'
    }, ]
    Group(sender_group).send({'text': json.dumps(resp)})
    Group(receiver_group).send({'text': json.dumps(resp)})


@channel_session_user_from_http
def ws_connect(message):
    # A user may be connected from various browsers or devices, so group all
    # the user's connections into one Group to send messages to that are
    # addressed to the user.
    group_kw = get_group_id_for_user(message.user)
    Group(group_kw).add(message.reply_channel)
    print('### WS connect: group_kw == "{}"'.format(group_kw))


@channel_session_user
def ws_receive(message):
    group_kw = get_group_id_for_user(message.user)
    payload = json.loads(message.content['text'])
    print('### WS receive: group_kw == {}'.format(group_kw))
    print('### WS receive: message[text] == {}'.format(message['text']))
    print('### WS receive: message.content == {}'.format(message.content))
    print('### WS receive: message.channel == {}'.format(message.channel))
    Channel(payload['action']).send(message.content)


@channel_session_user
def ws_disconnect(message):
    # Remove one of the user's connections from their Group, maybe they
    # turned off their phone or closed a browser tab.
    group_kw = get_group_id_for_user(message.user)
    Group(group_kw).discard(message.reply_channel)
    print('### WS disconnect: group_kw == {}'.format(group_kw))
