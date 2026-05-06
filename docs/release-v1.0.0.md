# EventHub v1.0.0

Title:
EventHub MVP: production-ready backend and frontend flows

## Highlights

- Production-ready Django/DRF backend
- React + Vite frontend
- JWT authentication
- Role-based access control
- Events and ticket types
- Atomic ticket booking with overselling protection
- QR ticket validation
- PDF ticket generation
- Organizer dashboard
- Single-elimination tournament engine
- Match result submission and bracket visualization
- Reviews and average rating annotations
- Persistent notifications
- WebSocket live updates
- Celery background tasks
- Redis caching
- Audit logs
- Swagger/OpenAPI documentation
- Docker Compose setup
- pytest/factory_boy/coverage

## Verification

- `docker compose config`: passed
- `docker compose exec backend python manage.py check`: passed, no issues
- `docker compose exec backend pytest`: passed, 594 passed, 1 skipped
- `cd frontend && npm run build`: passed

## Known Limitations

- No real payment provider yet
- No real camera QR scanner yet
- No custom tournament room WebSocket yet
- Frontend admin is focused on organizer flows
- Production cloud deployment requires environment-specific setup

## Suggested GitHub Release

Tag:
v1.0.0

Release title:
EventHub MVP: production-ready backend and frontend flows
