# Architecture

## Backend Apps

- `users`: custom email-based user model, authentication serializers and user permissions.
- `events`: event lifecycle, public browsing, categories, caching and event tasks.
- `tickets`: ticket types, availability validation and organizer management.
- `bookings`: booking model, booking service, QR generation, PDF generation and ticket usage.
- `tournaments`: tournament registration, single-elimination bracket generation and match results.
- `reviews`: event reviews, permissions and rating annotations.
- `notifications`: persistent notifications, Celery tasks and WebSocket consumers.
- `audit`: request id middleware and audit log capture.
- `common`: health checks and shared test/support utilities.

## Frontend Modules

- `api`: Axios API modules grouped by resource.
- `app`: top-level React app and providers.
- `components`: reusable UI, layout, auth, event, booking, organizer and tournament components.
- `hooks`: auth, notification and WebSocket hooks.
- `pages`: route-level screens.
- `router`: protected and role-based route configuration.
- `store`: auth state.
- `utils`: formatting, API data helpers, token storage and constants.

## Service Layer

Critical business rules are kept in backend service modules instead of serializers or views. The API layer validates HTTP input, permissions and response shape, then delegates booking, ticket validation, tournament bracket generation and match result promotion to service-layer functions.

## Critical Booking Transaction

Ticket booking uses `transaction.atomic` and locks the selected `TicketType` row with `select_for_update`. The service validates availability while the row is locked, creates the booking, updates `sold_count`, generates QR/PDF artifacts and schedules side effects after commit. This protects against overselling under concurrent requests.

## Tournament Bracket Engine

The tournament service builds a single-elimination bracket from registered participants, handles BYE advancement, links matches through `next_match` and `next_match_slot`, and promotes winners when organizers submit match results. The final match result marks the tournament as finished.

## Notifications And WebSocket Flow

Business events create persistent notifications. Notification tasks and services publish realtime messages through the Channels layer. Authenticated clients connect to:

```text
ws://localhost:8000/ws/notifications/?token=<access_token>
```

The frontend WebSocket hook receives notification events and invalidates relevant React Query keys so screens refresh without custom tournament-room sockets.

## Celery Tasks

Celery handles asynchronous work such as:

- Booking expiration.
- Event reminders.
- Notification cleanup.
- Email/notification side effects.

Celery uses Redis as broker/result backend and Celery Beat for periodic scheduling.

## Cache Invalidation

Public event data and popular event data are cached through Redis. Event, ticket, booking and review changes invalidate affected cache keys so public data remains fresh after organizer actions, purchases and review updates.
