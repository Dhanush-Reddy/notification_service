"""Integration tests for /notifications endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


SEND_PAYLOAD = {
    "user_id": "user_test_1",
    "channels": ["email"],
    "priority": "normal",
    "body": "Hello {{name}}, your order shipped.",
    "variables": {"name": "Alex"},
}


@pytest.mark.asyncio
async def test_send_notification_returns_202(client):
    with patch("app.queue.priority_queue.enqueue", new_callable=AsyncMock):
        resp = await client.post("/notifications", json=SEND_PAYLOAD)
    assert resp.status_code == 202
    data = resp.json()
    assert "notifications" in data
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["status"] == "queued"
    assert data["notifications"][0]["channel"] == "email"


@pytest.mark.asyncio
async def test_send_multi_channel(client):
    payload = {**SEND_PAYLOAD, "channels": ["email", "sms"], "user_id": "user_mc"}
    with patch("app.queue.priority_queue.enqueue", new_callable=AsyncMock):
        resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 202
    assert len(resp.json()["notifications"]) == 2


@pytest.mark.asyncio
async def test_get_notification_by_id(client):
    with patch("app.queue.priority_queue.enqueue", new_callable=AsyncMock):
        create_resp = await client.post("/notifications", json=SEND_PAYLOAD)
    assert create_resp.status_code == 202

    notif_id = create_resp.json()["notifications"][0]["id"]
    get_resp = await client.get(f"/notifications/{notif_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == notif_id


@pytest.mark.asyncio
async def test_get_nonexistent_notification_returns_404(client):
    resp = await client.get("/notifications/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_idempotency_same_key_returns_same_notification(client):
    payload = {
        **SEND_PAYLOAD,
        "user_id": "user_idem",
        "idempotency_key": "unique-key-abc",
    }
    with patch("app.queue.priority_queue.enqueue", new_callable=AsyncMock):
        resp1 = await client.post("/notifications", json=payload)
        resp2 = await client.post("/notifications", json=payload)

    assert resp1.status_code == 202
    assert resp2.status_code == 202
    # both should return the same notification ID
    id1 = resp1.json()["notifications"][0]["id"]
    id2 = resp2.json()["notifications"][0]["id"]
    assert id1 == id2


@pytest.mark.asyncio
async def test_invalid_channel_returns_422(client):
    payload = {**SEND_PAYLOAD, "channels": ["telegram"]}
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_priority_returns_422(client):
    payload = {**SEND_PAYLOAD, "priority": "urgent"}
    resp = await client.post("/notifications", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rate_limit_returns_429(client, mock_redis):
    from app.config import settings

    # make the pipeline return over-limit count
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 1, settings.rate_limit_max + 1, True])
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zadd = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    mock_redis.pipeline = MagicMock(return_value=pipe)
    mock_redis.zrange = AsyncMock(return_value=[])
    mock_redis.zrem = AsyncMock()

    resp = await client.post("/notifications", json={**SEND_PAYLOAD, "user_id": "user_ratelimit"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_opted_out_channel_returns_422(client, db_session):
    from app.repositories.preference_repo import PreferenceRepository

    user_id = "user_optout"
    # opt the user out of email
    repo = PreferenceRepository(db_session)
    await repo.upsert(user_id, "email", False)
    await db_session.commit()

    payload = {**SEND_PAYLOAD, "user_id": user_id}
    with patch("app.queue.priority_queue.enqueue", new_callable=AsyncMock):
        resp = await client.post("/notifications", json=payload)

    # all requested channels opted out → 422
    assert resp.status_code == 422
