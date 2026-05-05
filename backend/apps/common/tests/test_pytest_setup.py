import pytest

from apps.common.tests.factories import (
    PublishedEventFactory,
    TicketTypeFactory,
    UserFactory,
)


@pytest.mark.django_db
@pytest.mark.unit
def test_pytest_database_and_factories_work(api_client):
    user = UserFactory()
    event = PublishedEventFactory()
    ticket_type = TicketTypeFactory(event=event)

    response = api_client.get("/api/health/")

    assert response.status_code == 200
    assert user.email
    assert event.is_published is True
    assert ticket_type.event_id == event.id
