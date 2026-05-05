import factory

from apps.notifications.models import Notification

from .users import UserFactory


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    type = Notification.Type.SYSTEM
    title = factory.Sequence(lambda n: f"Notification {n}")
    message = "Factory notification"
    is_read = False
    entity_type = ""
    entity_id = ""
    metadata = factory.LazyFunction(dict)
