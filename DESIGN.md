# Design Document — Notification Service

## Architecture

```
                        ┌─────────────────────────┐
                        │       FastAPI App        │
                        │                          │
                        │  /notifications  /users  │
                        │     (routers)            │
                        └──────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      NotificationService     │
                    │  (rate limit → idempotency   │
                    │  → pref check → template     │
                    │  → DB insert → enqueue)       │
                    └──────┬───────────────┬────────┘
                           │               │
              ┌────────────▼───┐   ┌───────▼──────────┐
              │  PostgreSQL    │   │  Redis Sorted Set │
              │  (state, prefs │   │  (priority queue) │
              │   templates)   │   └───────┬───────────┘
              └────────────────┘           │
                                  ┌────────▼──────────┐
                                  │  Background Worker │
                                  │  (asyncio task)    │
                                  └────────┬───────────┘
                                           │
                    ┌──────────────────────┼──────────────────┐
                    │                      │                  │
           ┌────────▼──────┐   ┌──────────▼──┐   ┌──────────▼──┐
           │  MockEmail    │   │  MockSMS    │   │  MockPush   │
           └───────────────┘   └─────────────┘   └─────────────┘
```

## Database Schema

### `notifications`
Stores every notification request. One row per channel per request.

Key decisions:
- `priority` is a `SMALLINT` (0=critical → 3=low) rather than a string. Allows direct numeric comparison in the queue score.
- `idempotency_key` has a `UNIQUE` constraint at the **database level** — not just a code-level check. This prevents duplicate inserts even under concurrent requests.
- `status` has a `CHECK` constraint to enforce the state machine at the DB layer.
- All timestamps use `TIMESTAMPTZ` (timezone-aware) to avoid ambiguity across environments.

### `user_preferences`
Stores per-user, per-channel opt-in/out. Composite `UNIQUE(user_id, channel)` allows safe upserts via `INSERT ... ON CONFLICT DO UPDATE`.

If no preference row exists for a user/channel pair, the service defaults to **enabled** — users are opted in by default.

### `notification_templates`
Templates use string primary keys (e.g., `"order_shipped"`) so callers reference them by meaningful name. The body uses `{{variable}}` double-brace syntax per spec.

## Priority Queue

Uses a Redis **sorted set** (`ZADD` / `ZPOPMIN`).

Score formula: `priority_level × 10¹² + timestamp_ms`

This ensures:
1. Critical (0) always sorts before High (1), Normal (2), Low (3)
2. Within the same priority level, messages are processed FIFO

`ZPOPMIN` is atomic — no race condition between multiple worker instances dequeuing the same item.

Retried notifications use a **future timestamp** as their score so they naturally become eligible again only after the backoff delay.

## Failure Handling & Retries

The worker catches provider exceptions and applies exponential backoff with ±25% random jitter:

```
delay = min(300, 5 × 2^attempt) + uniform(0, delay × 0.25)
```

Jitter prevents thundering herd — if many notifications fail simultaneously, they don't all retry at exactly the same moment.

After 3 failed attempts, the notification is marked `failed` permanently.

State transitions:
```
pending → queued → sent → delivered
                 ↘ failed (after max retries)
```

## Scalability

Current setup runs the worker in-process with the API — fine for the demo.

To scale:
1. **Multiple API instances** behind a load balancer — stateless, no changes needed
2. **Separate worker processes** — multiple workers can safely pull from the same Redis sorted set because `ZPOPMIN` is atomic
3. **Read replicas** for notification history queries
4. **Partitioning** `notifications` table by `created_at` if row counts become large

At true high throughput (1000+ notifications/sec), Redis Streams with consumer groups would replace the sorted set to get acknowledgement semantics and better observability.

## Trade-offs

| Decision | Alternative | Why this choice |
|----------|-------------|-----------------|
| In-process worker | Celery / separate service | Reduces complexity for demo; swap-in ready since worker is isolated |
| Redis sorted set queue | RabbitMQ / SQS | No extra service needed, supports priority natively, persistent with AOF |
| SQLite for tests | Test Postgres container | Much faster CI; trade-off is minor dialect differences (CHECK constraints not enforced in SQLite) |
| Mock providers with 5% random failure | Always-succeed mocks | Exercises retry path without requiring real credentials |
| Rate limit per user (all channels) | Per user per channel | Simpler and harder to game; spec says "per user" |
