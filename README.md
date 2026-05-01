# EventHub

EventHub is a production-ready platform for events, tickets, and tournaments.

## Stack

- Backend: Django, Django REST Framework, PostgreSQL, Redis, Celery, Channels.
- Frontend: React, Tailwind CSS, Axios / React Query.

## Project Structure

```text
Tournament/
  backend/
    config/              # Django project configuration package
      settings/          # Environment-specific Django settings
    apps/                # Domain Django apps
      users/
      events/
      tickets/
      bookings/
      tournaments/
      reviews/
      notifications/
      audit/
      common/
    manage.py            # Django management entrypoint
    Dockerfile           # Backend container image
    entrypoint.sh        # Backend container startup script
    .env.example         # Example backend environment variables
    requirements.txt     # Backend Python dependencies
  frontend/
    src/
      api/               # API clients and request helpers
      components/        # Shared React components
      pages/             # Route-level React pages
      router/            # Client-side routing
      hooks/             # Shared React hooks
    package.json         # Frontend package manifest
  docker-compose.yml     # Backend Docker Compose infrastructure
  .gitignore
```

## Run with Docker

Create a backend environment file from the example:

```bash
cp backend/.env.example backend/.env
```

Build and run the backend infrastructure:

```bash
docker compose up --build
```

The backend will be available at http://localhost:8000.

Health endpoint:

```text
http://localhost:8000/api/health/
```

PostgreSQL runs inside Docker Compose as `postgres`.
Redis runs inside Docker Compose as `redis`.

Useful commands:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
docker compose down
docker compose down -v
```

## Tests

The default Django settings module is `config.settings.local`. For an explicit
test settings run from `backend/`:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

With Docker Compose:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test
```

This repository currently contains the base monorepo structure, backend foundation,
and Docker Compose infrastructure for Django, PostgreSQL, and Redis. Business logic,
models, and full API implementation will be added in later stages.
