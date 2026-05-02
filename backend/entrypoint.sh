#!/bin/sh
set -e

DB_HOST="${DATABASE_HOST:-postgres}"
DB_PORT="${DATABASE_PORT:-5432}"

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done

echo "PostgreSQL is available"

if [ "${SKIP_DJANGO_MAINTENANCE:-0}" != "1" ]; then
  python manage.py migrate
  python manage.py collectstatic --noinput
fi

exec "$@"
