import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.common.tests.factories import UserFactory
from config.asgi import application


IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
@pytest.mark.websocket
@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
async def test_websocket_valid_jwt_connects_and_ping_returns_pong():
    user = await sync_to_async(UserFactory)()
    token = str(AccessToken.for_user(user))
    communicator = WebsocketCommunicator(
        application,
        f"/ws/notifications/?token={token}",
    )

    connected, _ = await communicator.connect()
    initial_message = await communicator.receive_json_from()
    await communicator.send_json_to({"type": "ping"})
    pong_message = await communicator.receive_json_from()
    await communicator.disconnect()

    assert connected is True
    assert initial_message["type"] == "connection.accepted"
    assert pong_message == {"type": "pong"}
