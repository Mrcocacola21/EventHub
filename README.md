# EventHub

EventHub is a production-ready backend platform for events, tickets, and tournament-ready workflows built with Django and Django REST Framework.

The current backend includes event management, ticket types, atomic bookings, QR/PDF ticketing, audit logs, background jobs, Redis caching, persistent notifications, and live WebSocket notifications. Tournament and review modules are scaffolded/planned, but full tournament and review business logic is not implemented yet.

## Tech Stack

- Django
- Django REST Framework
- PostgreSQL
- Redis
- Celery and Celery Beat
- Django Channels
- SimpleJWT
- Docker Compose
- React frontend placeholder

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

## Testing

Recommended Docker checks:

```bash
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
```

Local checks can be run from `backend/` when PostgreSQL and Redis are available:

```bash
python manage.py makemigrations --check
python manage.py check
python manage.py test
```

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
  docker-compose.yml
  README.md
```

## Security And Production Notes

- Environment-based settings and secrets
- JWT authentication with SimpleJWT
- Role and object-level permissions
- Server-owned booking fields protected from client overrides
- Booking validation protected by QR tokens and permissions
- Overselling protection with row-level locking
- Audit logs for key business actions
- Request ID middleware and response header
- Read-only AuditLog admin
- Separate static and media storage paths
- Redis databases separated for Celery, cache, and Channels in the example env

## Useful Commands

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py makemigrations --check
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
docker compose down
docker compose down -v
```
