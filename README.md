# EventHub

EventHub is a production-ready backend platform for events, tickets, and tournament workflows built with Django and Django REST Framework.

The current backend includes event management, ticket types, atomic bookings, QR/PDF ticketing, a single-elimination tournament engine, event reviews, audit logs, background jobs, Redis caching, persistent notifications, and live WebSocket notifications.

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery and Celery Beat
- Django Channels
- SimpleJWT
- Docker Compose
- React
- Vite
- Tailwind CSS
- React Query

## Core Features

- Custom user model with email login
- JWT authentication and refresh tokens
- Role-based access control for users, organizers, and admins
- Event categories and event lifecycle management
- Ticket types with availability and sales-period validation
- Atomic booking with `transaction.atomic` and `select_for_update`
- Overselling protection
- QR ticket generation and validation
- PDF ticket generation and secure download
- Tournament engine with single-elimination brackets, participant registration, byes, winner promotion, match result submission, and automatic tournament finish
- Event reviews with one review per paid attendee, 1-5 ratings, average rating annotations, and admin moderation
- Production-style Django Admin dashboard
- Audit logs with request ID, IP address, and user-agent capture
- Celery background tasks for emails, booking expiration, reminders, and cleanup
- Redis caching for public events and popular events
- Persistent user notifications
- Django Channels WebSocket live notifications
- Automated test coverage

## API Overview

```text
GET  /api/health/
GET  /api/schema/
GET  /api/docs/
GET  /api/redoc/

POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
GET  /api/users/me/

GET  /api/event-categories/
GET  /api/events/
GET  /api/events/popular/
POST /api/events/
GET  /api/events/{id}/
PATCH /api/events/{id}/
POST /api/events/{id}/publish/
POST /api/events/{id}/cancel/
POST /api/events/{id}/finish/

GET  /api/events/{id}/tickets/
POST /api/events/{id}/tickets/

GET  /api/events/{id}/reviews/
POST /api/events/{id}/reviews/
GET  /api/reviews/{id}/
PATCH /api/reviews/{id}/
DELETE /api/reviews/{id}/

GET  /api/tournaments/
POST /api/tournaments/
GET  /api/tournaments/{id}/
PATCH /api/tournaments/{id}/
DELETE /api/tournaments/{id}/
POST /api/tournaments/{id}/open-registration/
POST /api/tournaments/{id}/cancel/
POST /api/tournaments/{id}/register/
POST /api/tournaments/{id}/start/
GET  /api/tournaments/{id}/bracket/
GET  /api/tournaments/{id}/participants/
POST /api/tournaments/{id}/participants/
GET  /api/tournaments/{id}/matches/
GET  /api/matches/{id}/
POST /api/matches/{id}/result/

GET  /api/bookings/
POST /api/bookings/
GET  /api/bookings/my/
POST /api/bookings/{id}/cancel/
POST /api/bookings/{id}/use/
GET  /api/bookings/{id}/download-pdf/

GET  /api/notifications/
POST /api/notifications/{id}/read/
POST /api/notifications/read-all/

WS   /ws/notifications/?token=<access_token>
```

## API Documentation

OpenAPI documentation is available at:

```text
GET /api/schema/
GET /api/docs/
GET /api/redoc/
```

Swagger UI supports JWT Bearer authorization through the `Authorize` button.
OpenAPI does not model WebSocket traffic well, so live notifications are documented here:

```text
ws://localhost:8000/ws/notifications/?token=<access_token>
```

Client ping:

```json
{
  "type": "ping"
}
```

Server pong:

```json
{
  "type": "pong"
}
```

Notification payload:

```json
{
  "type": "notification",
  "notification": {
    "id": 1,
    "type": "BOOKING_CREATED",
    "title": "Ticket booked",
    "message": "...",
    "is_read": false,
    "entity_type": "Booking",
    "entity_id": "1",
    "metadata": {},
    "created_at": "..."
  }
}
```

## Docker Usage

Create the backend environment file:

```bash
cp backend/.env.example backend/.env
```

Build and start the stack:

```bash
docker compose up --build
```

Run backend management commands:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py test
```

The backend is available at:

```text
http://localhost:8000
```

## Frontend Usage

Create the frontend environment file:

```bash
cd frontend
cp .env.example .env
```

Install dependencies and run the Vite dev server:

```bash
npm install
npm run dev
```

Build the production bundle:

```bash
npm run build
```

The frontend is available at:

```text
http://localhost:5173
```

The default frontend environment points to:

```text
Backend API: http://localhost:8000/api
WebSocket:   ws://localhost:8000/ws
```

Implemented frontend foundation:

- React, Vite, Tailwind CSS, Axios, and React Query
- JWT auth with access token refresh
- Protected routes and role-based organizer/admin routes
- Shared layout, navigation, reusable UI components, and API modules

Implemented frontend user-facing flows:

- Events list with filters and pagination support
- Event details with ticket types
- Auth-aware ticket booking
- My bookings list with status filtering
- Booking details page
- QR code display
- PDF ticket download
- Booking cancellation for eligible bookings

Implemented organizer dashboard flows:

- Organizer/admin dashboard with event summary
- Create and edit events
- Publish, cancel, and finish events
- Manage ticket types for an event
- View event bookings with status, usage, and user filters
- Download booking PDF tickets from organizer booking lists
- Validate tickets by manual booking ID entry
- Organizer tournament list, creation, and management
- Open tournament registration, start tournaments, and cancel tournaments
- Submit match results from the organizer bracket view

Implemented tournament flows:

- Public tournaments list with status, type, and search filters
- Tournament details with participant registration
- Participant list
- Single-elimination bracket visualization
- Match winner highlighting and BYE handling
- Notification WebSocket hook that refreshes tournament, bracket, match, and
  notification queries for tournament-related notifications

Manual booking ID validation is available in the organizer QR Check page.
Camera QR scanning is planned for a later stage when a frontend scanner and
backend token validation endpoint are connected.

Tournament live updates currently use the existing notification WebSocket
(`ws://localhost:8000/ws/notifications/?token=<access_token>`) to refresh data.
There is no custom tournament room WebSocket yet, no drag-and-drop bracket
editing, and tournament support is currently single-elimination only.

## Testing

Django test runner:

```bash
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
```

Pytest:

```bash
docker compose exec backend pytest
```

Coverage:

```bash
docker compose exec backend pytest --cov=apps --cov=config --cov-report=term-missing
docker compose exec backend pytest --cov=apps --cov=config --cov-report=html
```

Local checks can be run from `backend/` when PostgreSQL and Redis are available:

```bash
python manage.py makemigrations --check
python manage.py check
python manage.py test
pytest
pytest --cov=apps --cov=config --cov-report=term-missing
```

Pytest uses `config.settings.test`. Celery tasks run eagerly, cache uses locmem,
Channels uses the in-memory channel layer, and QR/PDF tests use a temporary
`MEDIA_ROOT`.

## Background Services

Docker Compose includes:

- `backend`
- `postgres`
- `redis`
- `celery_worker`
- `celery_beat`

Useful logs:

```bash
docker compose logs -f backend
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

## Project Structure

```text
Tournament/
  backend/
    apps/
      audit/
      bookings/
      common/
      events/
      notifications/
      reviews/
      tickets/
      tournaments/
      users/
    config/
      settings/
    manage.py
    requirements.txt
  frontend/
    src/
      api/
      app/
      components/
      hooks/
      pages/
      router/
      store/
      utils/
  docker-compose.yml
  README.md
```

## Security And Production Notes

- Environment-based settings and secrets
- JWT authentication with SimpleJWT
- Role and object-level permissions
- Server-owned booking fields protected from client overrides
- Booking validation protected by QR tokens and permissions
- Tournament organizer/admin permissions for tournament management
- Review creation restricted to paid attendees, with published reviews used for event rating summaries
- Overselling protection with row-level locking
- Audit logs for key business actions
- Request ID middleware and response header
- Read-only AuditLog admin
- Separate static and media storage paths
- Redis databases separated for Celery, cache, and Channels in the example env
- Tournament support is currently single-elimination only; double-elimination and round-robin formats are not implemented

## Useful Commands

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
docker compose down
docker compose down -v
```
