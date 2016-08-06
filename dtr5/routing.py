from channels import route
from django.conf import settings

from dtr5app.consumers import ws_receive, ws_disconnect, ws_connect, \
    message_consumer

ws_path_re = r'^/chat/(?P<username>' + settings.RSTR_USERNAME + r')$'

channel_routing = [
    route('websocket.connect', ws_connect, path=ws_path_re),
    route('websocket.disconnect', ws_disconnect),
    route('websocket.receive', ws_receive),

    route('chat.receive', message_consumer),

    # route_class(ChatConsumer, path=r'^/chat/'),
]
