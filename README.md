# Notification Service

A backend service for delivering notifications across Email, SMS, and Push channels with priority queuing, retry logic, and user preferences.

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Framework | FastAPI | Async-native, auto OpenAPI docs, good type hint support |
| Database | PostgreSQL + SQLAlchemy (async) | Relational integrity for preferences and delivery tracking |
| Queue | Redis sorted sets | Lightweight priority queue, persistence via AOF, no separate broker needed |
| Migrations | Alembic | Standard with SQLAlchemy, easy to review diffs |
| Testing | pytest + pytest-asyncio + httpx | Async test support, no test server needed |

## Local Setup

**Requirements:** Python 3.11+, PostgreSQL, Redis

```bash
cd notification-service

# copy and configure environment
cp .env.example .env

# install dependencies
pip install -r requirements.txt

# run the app (migrations apply automatically on startup)
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

### Docker (easier)

```bash
docker-compose up --build
```

## Running Tests

Tests use SQLite in-memory — no Postgres or Redis required.

```bash
pip install -r requirements.txt
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

## API Documentation

Interactive docs at `/docs` (Swagger UI) or `/redoc` when the app is running.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/notifications` | Queue a notification (returns 202) |
| `GET` | `/notifications/{id}` | Get notification status |
| `GET` | `/users/{userId}/notifications` | Paginated notification history |
| `POST` | `/users/{userId}/preferences` | Set channel opt-in/out |
| `GET` | `/users/{userId}/preferences` | Get all channel preferences |

### Example: Send a notification

```bash
curl -X POST http://localhost:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "channels": ["email", "sms"],
    "priority": "high",
    "subject": "Your order shipped",
    "body": "Hello {{name}}, your order {{order_id}} has shipped.",
    "variables": {"name": "Alex", "order_id": "ORD-456"},
    "idempotency_key": "order-456-shipped"
  }'
```

### Priority levels

| Value | Meaning |
|-------|---------|
| `critical` | Processed first |
| `high` | |
| `normal` | Default |
| `low` | Processed last |

## Assumptions

- Authentication/authorization is handled upstream (e.g., API gateway). No auth in this service.
- User profiles live in a separate service — this service only stores `user_id` as a string.
- Template storage is in the database. Templates can be pre-seeded via Alembic data migrations.
- "Delivered" status requires the mock provider to confirm — in production this would come from webhooks from SendGrid/Twilio/etc. For now, `sent` and `delivered` are both set on successful mock delivery.
- Rate limiting is per `user_id` across all channels combined (100 requests/hour).
- The worker runs in the same process as the API for demo purposes. In production, this would be a separate worker service.
