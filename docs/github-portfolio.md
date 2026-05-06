# GitHub Portfolio Setup

## About Description

Use this repository description:

```text
Production-ready event and tournament platform with Django, DRF, React, PostgreSQL, Redis, Celery, Channels, atomic booking, QR validation, and PDF tickets.
```

## Topics

Add these GitHub topics:

```text
django
django-rest-framework
drf
react
vite
tailwindcss
postgresql
redis
celery
django-channels
jwt
openapi
swagger
pytest
docker
websocket
portfolio-project
event-management
ticket-booking
tournament-platform
```

GitHub CLI:

```bash
gh repo edit Mrcocacola21/EventHub \
  --description "Production-ready event and tournament platform with Django, DRF, React, PostgreSQL, Redis, Celery, Channels, atomic booking, QR validation, and PDF tickets." \
  --add-topic django \
  --add-topic django-rest-framework \
  --add-topic drf \
  --add-topic react \
  --add-topic vite \
  --add-topic tailwindcss \
  --add-topic postgresql \
  --add-topic redis \
  --add-topic celery \
  --add-topic django-channels \
  --add-topic jwt \
  --add-topic openapi \
  --add-topic swagger \
  --add-topic pytest \
  --add-topic docker \
  --add-topic websocket \
  --add-topic portfolio-project \
  --add-topic event-management \
  --add-topic ticket-booking \
  --add-topic tournament-platform
```

GitHub UI:

1. Open the repository page.
2. Click the gear icon near the About section.
3. Paste the About description above.
4. Add the topics above.
5. Save changes.

## Release v1.0.0

GitHub CLI:

```bash
git tag -a v1.0.0 -m "EventHub MVP: production-ready backend and frontend flows"
git push origin v1.0.0
gh release create v1.0.0 --title "EventHub MVP: production-ready backend and frontend flows" --notes-file docs/release-v1.0.0.md
```

GitHub UI:

1. Open the repository on GitHub.
2. Go to Releases.
3. Click "Draft a new release".
4. Set the tag to `v1.0.0`.
5. Set the title to `EventHub MVP: production-ready backend and frontend flows`.
6. Copy the content from `docs/release-v1.0.0.md`.
7. Publish the release.
