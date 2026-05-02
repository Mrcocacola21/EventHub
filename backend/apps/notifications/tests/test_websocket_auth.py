from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from config.asgi import application

IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

User = get_user_model()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class NotificationWebSocketAuthTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ws-user@example.com",
            password="StrongPass123!",
        )

    def token_for(self, user):
        return str(AccessToken.for_user(user))

    def test_websocket_without_token_is_rejected(self):
        async_to_sync(self._assert_rejected)("/ws/notifications/")

    def test_websocket_with_invalid_token_is_rejected(self):
        async_to_sync(self._assert_rejected)(
            "/ws/notifications/?token=not-a-valid-token"
        )

    def test_websocket_with_refresh_token_is_rejected(self):
        token = str(RefreshToken.for_user(self.user))

        async_to_sync(self._assert_rejected)(f"/ws/notifications/?token={token}")

    def test_websocket_with_valid_access_token_connects(self):
        async_to_sync(self._assert_connects)()

    def test_ping_returns_pong(self):
        async_to_sync(self._assert_ping_returns_pong)()

    async def _assert_rejected(self, path):
        communicator = WebsocketCommunicator(application, path)
        connected, close_code = await communicator.connect()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)

    async def _assert_connects(self):
        token = self.token_for(self.user)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={token}",
        )

        connected, _ = await communicator.connect()
        message = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertTrue(connected)
        self.assertEqual(message["type"], "connection.accepted")

    async def _assert_ping_returns_pong(self):
        token = self.token_for(self.user)
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={token}",
        )

        connected, _ = await communicator.connect()
        await communicator.receive_json_from()
        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertTrue(connected)
        self.assertEqual(response, {"type": "pong"})
