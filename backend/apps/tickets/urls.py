from django.urls import path

from .views import TicketTypeViewSet

event_ticket_types = TicketTypeViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)
ticket_type_detail = TicketTypeViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path(
        "events/<int:event_id>/tickets/",
        event_ticket_types,
        name="event-ticket-types-list",
    ),
    path(
        "ticket-types/<int:pk>/",
        ticket_type_detail,
        name="ticket-type-detail",
    ),
]
