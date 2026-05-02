from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application

IN_MEMORY_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

User = get_user_model()


@override_settings(CHANNEL_LAYERS=IN_MEMORY_CHANNEL_LAYERS)
class NotificationConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ws-owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = User.objects.create_user(
            email="ws-other@example.com",
            password="StrongPass123!",
        )

    def token_for(self, user):
        return str(AccessToken.for_user(user))

    def test_user_receives_messages_for_own_group(self):
        async_to_sync(self._assert_own_group_delivery)()

    def test_user_does_not_receive_messages_for_another_user_group(self):
        async_to_sync(self._assert_other_group_is_isolated)()

    async def _connect_user(self, user):
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={self.token_for(user)}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()
        return communicator

    async def _assert_own_group_delivery(self):
        communicator = await self._connect_user(self.user)
        payload = {
            "type": "notification",
            "notification": {
                "id": 1,
                "type": "BOOKING_CREATED",
                "title": "Ticket booked",
                "message": "Booked",
                "is_read": False,
                "entity_type": "Booking",
                "entity_id": "1",
                "metadata": {},
                "created_at": "2026-05-01T00:00:00Z",
            },
        }

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            f"user_notifications_{self.user.id}",
            {
                "type": "notification.event",
                "payload": payload,
            },
        )
        response = await communicator.receive_json_from()
        await communicator.disconnect()

        self.assertEqual(response, payload)

    async def _assert_other_group_is_isolated(self):
        communicator = await self._connect_user(self.user)
        channel_layer = get_channel_layer()

        await channel_layer.group_send(
            f"user_notifications_{self.other_user.id}",
            {
                "type": "notification.event",
                "payload": {
                    "type": "notification",
                    "notification": {"id": 99},
                },
            },
        )

        self.assertTrue(await communicator.receive_nothing(timeout=0.1))
        await communicator.disconnect()
