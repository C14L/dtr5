# from channels import route

# from dtr5app.consumers import ws_receive, ws_disconnect, ws_connect, \
#     chat_init, chat_receive, chats_init, authuser_sub

# # ws_path_re = r'^/api/v1/chat/(?P<username>' + settings.RSTR_USERNAME + r')$'
# ws_path_re = r'^/api/v1/ws$'
# channel_routing = [
#     route('websocket.connect', ws_connect, path=ws_path_re),
#     route('websocket.disconnect', ws_disconnect),
#     route('websocket.receive', ws_receive),

#     route('chats.init', chats_init),
#     route('chat.init', chat_init),
#     route('chat.receive', chat_receive),

#     route('authuser.sub', authuser_sub),
# ]

from django.conf.urls import url

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# from chat.consumers import AdminChatConsumer, PublicChatConsumer
# from aprs_news.consumers import APRSNewsConsumer

application = ProtocolTypeRouter({
    # WebSocket chat handler
    "websocket": AuthMiddlewareStack(
        URLRouter([
            # url(r"^chat/admin/$", AdminChatConsumer),
            # url(r"^chat/$", PublicChatConsumer),
        ])
    ),

    # Using the third-party project frequensgi, which provides an APRS protocol
    # "aprs": APRSNewsConsumer,

})
