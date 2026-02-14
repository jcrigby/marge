"""
CTS -- Webhook API Depth Tests

Tests POST /api/webhook/{webhook_id} with state-setting payloads,
event-firing payloads, and default (empty) webhook events.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_webhook_sets_entity_state(rest):
    """Webhook with entity_id + state sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wh_state_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={"entity_id": eid, "state": "triggered", "attributes": {"source": "webhook"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "State updated" in data.get("message", "")

    state = await rest.get_state(eid)
    assert state["state"] == "triggered"
    assert state["attributes"]["source"] == "webhook"


async def test_webhook_fires_named_event(rest):
    """Webhook with event_type fires that event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={"event_type": f"custom_event_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "fired" in data.get("message", "").lower()


async def test_webhook_default_fires_webhook_event(rest):
    """Webhook with empty body fires webhook.<id> event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert f"webhook.hook_{tag}" in data.get("message", "")


async def test_webhook_no_body(rest):
    """Webhook with no JSON body still returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_webhook_state_with_attributes(rest):
    """Webhook state-set with complex attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wh_attrs_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={
            "entity_id": eid,
            "state": "active",
            "attributes": {"nested": {"key": "val"}, "list": [1, 2, 3]},
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "active"
    assert state["attributes"]["nested"]["key"] == "val"
    assert state["attributes"]["list"] == [1, 2, 3]


async def test_webhook_state_only_no_attrs(rest):
    """Webhook with entity_id + state but no attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wh_noattr_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        json={"entity_id": eid, "state": "minimal"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "minimal"


async def test_webhook_multiple_calls_same_id(rest):
    """Multiple webhook calls to same ID work independently."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wh_multi_{tag}"
    for i in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/webhook/hook_multi",
            json={"entity_id": eid, "state": f"call_{i}"},
            headers=rest._headers(),
        )
        assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "call_2"
