# Deployment Guide

## Prerequisites

- Docker and Docker Compose.
- Production PostgreSQL.
- Production Redis.
- Domain name and HTTPS termination.
- Environment-specific secret storage.

## Environment Variables

Start from the examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

For production, set at minimum:

- `DEBUG=False`.
- A strong `SECRET_KEY`.
- Production `ALLOWED_HOSTS`.
- Production PostgreSQL credentials.
- Production Redis URLs.
- Production `CORS_ALLOWED_ORIGINS`.
- Real email backend settings.

Never commit real `.env` files.

## Docker Compose

Build and start the stack:

```bash
docker compose up --build
```

The development compose file includes backend, PostgreSQL, Redis, Celery worker, Celery Beat and frontend services. Production deployments can reuse the service split, but should move secrets, ports, volumes and reverse proxy settings into environment-specific infrastructure.

## Database Migrations

Run migrations before serving traffic:

```bash
docker compose exec backend python manage.py migrate
```

Create an admin user when needed:

```bash
docker compose exec backend python manage.py createsuperuser
```

## Static Files

The backend entrypoint runs `collectstatic` unless `SKIP_DJANGO_MAINTENANCE=1` is set. In production, serve static files through Nginx or another reverse proxy/CDN.

Media files contain generated PDF tickets and QR-related assets. Use persistent storage in production. S3-compatible storage is a natural next step for cloud deployment.

## Celery Worker And Beat

Run Celery worker and Celery Beat as separate long-running processes:

```bash
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Celery depends on Redis and PostgreSQL. Keep worker and beat logs monitored because booking expiration, reminders and notification cleanup run asynchronously.

## Redis

Redis is used for:

- Celery broker/result backend.
- Django cache.
- Django Channels layer.

Use separate Redis databases or separate Redis instances in production if operational isolation is required.

## Production Checklist

- Set `DEBUG=False`.
- Set a strong `SECRET_KEY`.
- Set explicit `ALLOWED_HOSTS`.
- Configure HTTPS and secure proxy headers.
- Configure Nginx or another reverse proxy.
- Run Django through Gunicorn or Daphne/ASGI depending on WebSocket deployment needs.
- Configure real email delivery.
- Configure persistent PostgreSQL and Redis volumes or managed services.
- Configure database backups.
- Configure monitoring and structured logging.
- Configure persistent media storage, for example S3 later.
- Restrict admin access and rotate credentials.
- Run `python manage.py check --deploy` before launch.
