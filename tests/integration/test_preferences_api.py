"""Integration tests for /users/:userId/preferences endpoints."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_set_preference(client):
    resp = await client.post(
        "/users/user_pref_1/preferences",
        json={"channel": "email", "is_enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "email"
    assert data["is_enabled"] is False


@pytest.mark.asyncio
async def test_get_preferences_empty_for_new_user(client):
    resp = await client.get("/users/brand_new_user/preferences")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_preferences_returns_set_values(client):
    user_id = "user_pref_get"
    await client.post(
        f"/users/{user_id}/preferences",
        json={"channel": "sms", "is_enabled": True},
    )
    await client.post(
        f"/users/{user_id}/preferences",
        json={"channel": "push", "is_enabled": False},
    )

    resp = await client.get(f"/users/{user_id}/preferences")
    assert resp.status_code == 200
    prefs = {p["channel"]: p["is_enabled"] for p in resp.json()}
    assert prefs["sms"] is True
    assert prefs["push"] is False


@pytest.mark.asyncio
async def test_upsert_updates_existing(client):
    user_id = "user_pref_upsert"
    # set enabled
    await client.post(
        f"/users/{user_id}/preferences",
        json={"channel": "email", "is_enabled": True},
    )
    # disable it
    resp = await client.post(
        f"/users/{user_id}/preferences",
        json={"channel": "email", "is_enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is False

    # verify the read reflects the update
    get_resp = await client.get(f"/users/{user_id}/preferences")
    prefs = {p["channel"]: p["is_enabled"] for p in get_resp.json()}
    assert prefs["email"] is False


@pytest.mark.asyncio
async def test_invalid_channel_preference_returns_422(client):
    resp = await client.post(
        "/users/user_x/preferences",
        json={"channel": "fax", "is_enabled": True},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_user_notifications_empty(client):
    resp = await client.get("/users/nobody/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
