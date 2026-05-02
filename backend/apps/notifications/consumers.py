from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = f"user_notifications_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "type": "connection.accepted",
                "message": "Connected to EventHub notifications",
            }
        )

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        group_name = getattr(self, "group_name", None)
        if user and user.is_authenticated and group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def notification_event(self, event):
        await self.send_json(event["payload"])
