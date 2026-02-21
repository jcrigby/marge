"""
CTS -- Webhook + Event Integration Tests

Tests the webhook endpoint's interaction with state machine and
automation engine: state setting via webhook, event firing via webhook,
default webhook event, and automation triggering via webhook events.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


# ── Webhook State Setting ──────────────────────────────────

@pytest.mark.marge_only
async def test_webhook_sets_entity_state(rest):
    """Webhook with entity_id + state sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.webhook_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_{tag}",
        json={"entity_id": eid, "state": "42"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "State updated" in data.get("message", "")

    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "42"


@pytest.mark.marge_only
async def test_webhook_sets_state_with_attributes(rest):
    """Webhook with attributes sets entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.webhook_attr_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/attr_hook_{tag}",
        json={
            "entity_id": eid,
            "state": "23.5",
            "attributes": {"unit_of_measurement": "C", "friendly_name": "Webhook Temp"},
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "23.5"
    assert state["attributes"]["unit_of_measurement"] == "C"
    assert state["attributes"]["friendly_name"] == "Webhook Temp"


@pytest.mark.marge_only
async def test_webhook_overwrites_existing_state(rest):
    """Webhook updates an already-existing entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.webhook_ow_{tag}"
    await rest.set_state(eid, "old_value")

    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/overwrite_{tag}",
        json={"entity_id": eid, "state": "new_value"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "new_value"


# ── Webhook Event Firing ──────────────────────────────────

@pytest.mark.marge_only
async def test_webhook_fires_event(rest):
    """Webhook with event_type fires an event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/event_hook_{tag}",
        json={"event_type": f"test_webhook_event_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Event" in data.get("message", "") or "fired" in data.get("message", "")


@pytest.mark.marge_only
async def test_webhook_default_fires_webhook_event(rest):
    """Webhook with no entity_id or event_type fires webhook.<id> event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/default_{tag}",
        json={"some_data": "value"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "fired" in data.get("message", "").lower()
    assert f"webhook.default_{tag}" in data.get("message", "")


@pytest.mark.marge_only
async def test_webhook_empty_body(rest):
    """Webhook with empty/no body fires default event."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/empty_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "fired" in data.get("message", "").lower()


# ── Webhook + Automation Integration ──────────────────────

@pytest.mark.marge_only
async def test_webhook_event_triggers_automation(rest):
    """Webhook firing bedside_button_pressed triggers goodnight."""
    # Set up lights on so we can verify goodnight turns them off
    await rest.set_state("light.bedroom", "on")
    await rest.set_state("lock.front_door", "unlocked")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.goodnight_routine")
    count_before = s1["attributes"].get("current", 0)

    # Fire event via webhook
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/bedside",
        json={"event_type": "bedside_button_pressed"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.goodnight_routine")
    assert s2["attributes"].get("current", 0) > count_before


@pytest.mark.marge_only
async def test_webhook_state_set_triggers_automation(rest):
    """Webhook setting smoke_detector to on triggers emergency automation."""
    # Set up baseline
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await rest.set_state("lock.front_door", "locked")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency"
    })
    await asyncio.sleep(0.1)

    # Set state via webhook
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/smoke_test",
        json={"entity_id": "binary_sensor.smoke_detector", "state": "on"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.5)

    # Emergency automation should have fired, unlocking front door
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


# ── Multiple webhooks ──────────────────────────────────────

async def test_rapid_webhook_state_updates(rest):
    """Multiple rapid webhook state updates, last one wins."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.webhook_rapid_{tag}"
    for i in range(10):
        await rest.client.post(
            f"{rest.base_url}/api/webhook/rapid_{tag}",
            json={"entity_id": eid, "state": str(i)},
            headers=rest._headers(),
        )
    state = await rest.get_state(eid)
    assert state["state"] == "9"


async def test_webhook_different_ids_independent(rest):
    """Different webhook IDs are independent endpoints."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.wh_a_{tag}"
    eid2 = f"sensor.wh_b_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_a_{tag}",
        json={"entity_id": eid1, "state": "from_a"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_b_{tag}",
        json={"entity_id": eid2, "state": "from_b"},
        headers=rest._headers(),
    )

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "from_a"
    assert s2["state"] == "from_b"
