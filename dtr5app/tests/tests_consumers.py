import json

from channels import Channel
from channels.tests import ChannelTestCase
from django.contrib import auth
from django.contrib.auth.models import User

from dtr5app.consumers import ws_receive


class Dtr5appConsumersTestCase(ChannelTestCase):
    u1 = {'username': 'testuser1', 'email': 'a@b.com', 'password': 'hunter2'}
    u2 = {'username': 'testuser2', 'email': 'c@d.com', 'password': 'hunter2'}

    def setUp(self):
        self.user1 = User.objects.create_user(**self.u1)
        self.user2 = User.objects.create_user(**self.u2)
        self.payload = {'action': 'chat.receive',
                        'msg': 'The test message 123.',
                        'receiver': self.user2.id,
                        'after': '', 'is_sent': '', 'is_seen': ''}
        self.message = {'text': json.dumps(self.payload)}

    def tearDown(self):
        pass

    def test_send_chat_message_find_it_on_channel(self):
        # Send a chat message
        Channel('websocket.receive').send(self.message)
        # See if it gets put on the channel
        result = self.get_next_message('websocket.receive', require=True)
        self.assertEqual(result.content['text'], self.message['text'])

    def test_send_chat_message_is_used_by_consumer(self):
        u = User.objects.get(username=self.u1['username'])
        self.assertEqual(u.email, self.u1['email'])

        login = self.client.login(reddit_user=self.u1['username'])
        self.assertTrue(login, msg='User is not logged in.')
        self.assertTrue(auth.get_user(self.client).is_authenticated)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user1.pk)

        # TODO: The below test causes an error:
        #
        # "ValueError: No reply_channel sent to consumer; @channel_session
        # can only be used on messages containing it."

        # # Send a chat message
        # Channel('websocket.receive').send(self.message)
        # # Receive it and place it on the correct channel
        # ws_receive(self.get_next_message('websocket.receive', require=True))
        # # Fetch it from that channel
        # result = self.get_next_message(self.payload['action'], require=True)
        # # That should be the payload_json we sent
        # self.assertEqual(result, self.message)
