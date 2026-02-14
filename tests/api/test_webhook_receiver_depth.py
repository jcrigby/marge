"""
CTS -- Webhook Receiver Depth Tests

Tests POST /api/webhook/{webhook_id} with three modes:
1. Set entity state (entity_id + state + attributes)
2. Fire named event (event_type + data)
3. Default webhook event (no payload)
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Webhook → Set State ─────────────────────────────────

async def test_webhook_set_state(rest):
    """Webhook with entity_id + state sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wh_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_{tag}",
        json={"entity_id": eid, "state": "42"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "State updated" in data.get("message", "")
    state = await rest.get_state(eid)
    assert state["state"] == "42"


async def test_webhook_set_state_with_attributes(rest):
    """Webhook with attributes sets entity state and attrs."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wha_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_{tag}",
        json={
            "entity_id": eid,
            "state": "100",
            "attributes": {"unit": "W", "friendly_name": f"Webhook {tag}"},
        },
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "100"
    assert state["attributes"]["unit"] == "W"


async def test_webhook_update_existing_entity(rest):
    """Webhook can update an existing entity's state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.whu_{tag}"
    await rest.set_state(eid, "old")
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/update_{tag}",
        json={"entity_id": eid, "state": "new"},
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "new"


# ── Webhook → Fire Event ───────────────────────────────

async def test_webhook_fire_event(rest):
    """Webhook with event_type fires event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/event_{tag}",
        json={"event_type": f"test.event_{tag}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "fired" in data.get("message", "").lower()


# ── Webhook → Default Event ────────────────────────────

async def test_webhook_default_event(rest):
    """Webhook with no payload fires webhook.<id> event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/default_{tag}",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert f"webhook.default_{tag}" in data.get("message", "")


async def test_webhook_no_body(rest):
    """Webhook with no body at all still succeeds."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/nobody_{tag}",
    )
    # Should succeed (empty body = empty JSON object)
    assert resp.status_code in (200, 422)


# ── Multiple Webhooks ──────────────────────────────────

async def test_different_webhook_ids_independent(rest):
    """Different webhook IDs set different entities."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.wh1_{tag}"
    eid2 = f"sensor.wh2_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/webhook/a_{tag}",
        json={"entity_id": eid1, "state": "A"},
    )
    await rest.client.post(
        f"{rest.base_url}/api/webhook/b_{tag}",
        json={"entity_id": eid2, "state": "B"},
    )
    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "A"
    assert s2["state"] == "B"
