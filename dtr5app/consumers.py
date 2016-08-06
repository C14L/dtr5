from channels import Channel, Group
from channels.auth import channel_session_user, channel_session_user_from_http
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from dtr5app.models import Message


def get_view_user_id_from_group_kw(group_kw, auth_user_id):
    user_ids = [int(a) for a in group_kw.split('-', 2)[1:3]]
    return [a for a in user_ids if a != auth_user_id][0]


@channel_session_user
def message_consumer(message):
    group_kw = message.channel_session['group_kw']
    print('### message_consumer: group_kw == "{}"'.format(group_kw))
    view_user_id = get_view_user_id_from_group_kw(group_kw, message.user.id)
    print('### message_consumer: view_user_id == "{}"'.format(view_user_id))
    Message.objects.create(msg=message['text'],
                           sender=message.user, receiver_id=view_user_id)
    Group(group_kw).send({'text': message['text']})


@channel_session_user_from_http
def ws_connect(message, username):
    auth_user_id = message.user.id
    view_user_id = get_object_or_404(User, username=username).id
    group_kw = 'chat-{}-{}'.format(*sorted([auth_user_id, view_user_id]))
    print('- - - - - - - - - - - - - - - - - - - - - - - - -')
    print('### WS connect: username == "{}"'.format(username))
    print('### WS connect: auth_user_id == "{}"'.format(auth_user_id))
    print('### WS connect: view_user_id == "{}"'.format(view_user_id))
    print('### WS connect: group_kw == "{}"'.format(group_kw))
    message.channel_session['group_kw'] = group_kw
    Group(group_kw).add(message.reply_channel)


@channel_session_user
def ws_receive(message):
    group_kw = message.channel_session['group_kw']
    # message.content == "{'text': 'some text', 'path': '/chat/C14L',
    #              'reply_channel': 'websocket.send!YQGbKqEwfRpN', 'order': 1}"
    print('- - - - - - - - - - - - - - - - - - - - - - - - -')
    print('### WS receive: group_kw == {}'.format(group_kw))
    print('### WS receive: message[text] == {}'.format(message['text']))
    Channel("chat.receive").send(message.content)
    # Group(group_kw).send({'text': message['text']})


@channel_session_user
def ws_disconnect(message):
    group_kw = message.channel_session['group_kw']
    Group(group_kw).discard(message.reply_channel)
    print('- - - - - - - - - - - - - - - - - - - - - - - - -')
    print('### WS disconnect: group_kw == {}'.format(group_kw))
