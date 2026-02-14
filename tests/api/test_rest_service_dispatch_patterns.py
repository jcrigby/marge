"""
CTS -- REST Service Dispatch Pattern Tests

Tests advanced service call patterns: target.entity_id, array
entity_ids, automation trigger/enable/disable services, and
persistent_notification CRUD via REST service dispatch.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Array entity_id ──────────────────────────────────────

async def test_service_array_entity_id(rest):
    """Service call with array entity_id affects all entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.arr_{tag}_{i}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": eids},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_service_single_entity_id_string(rest):
    """Service call with string entity_id works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.single_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── target.entity_id pattern ─────────────────────────────

async def test_service_target_entity_id(rest):
    """Service call with target.entity_id dispatches correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.target_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"target": {"entity_id": eid}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_service_target_array_entity_id(rest):
    """Service call with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.tarr_{tag}_{i}" for i in range(2)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"target": {"entity_id": eids}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Automation services ──────────────────────────────────

async def test_automation_trigger_service(rest):
    """automation.trigger fires the automation's actions."""
    # Just verify the API accepts the call without error
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.nonexistent_trigger_test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_automation_turn_off_service(rest):
    """automation.turn_off disables an automation (sets state to off)."""
    # The loaded automations should have some real IDs
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if len(autos) > 0:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        await rest.call_service("automation", "turn_off", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "off"

        # Re-enable it
        await rest.call_service("automation", "turn_on", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_automation_toggle_service(rest):
    """automation.toggle flips enabled state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if len(autos) > 0:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        # Get current state
        s1 = await rest.get_state(eid)
        original = s1["state"]

        # Toggle
        await rest.call_service("automation", "toggle", {"entity_id": eid})
        s2 = await rest.get_state(eid)
        assert s2["state"] != original

        # Toggle back
        await rest.call_service("automation", "toggle", {"entity_id": eid})
        s3 = await rest.get_state(eid)
        assert s3["state"] == original


# ── Persistent notification via service ──────────────────

async def test_notification_create_via_service(rest):
    """persistent_notification.create via service endpoint."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"svc_notif_{tag}",
            "title": f"Test {tag}",
            "message": "Created via service dispatch",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify notification exists
    await asyncio.sleep(0.3)
    nr = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = nr.json()
    ids = [n["notification_id"] for n in notifs]
    assert f"svc_notif_{tag}" in ids


async def test_notification_dismiss_via_service(rest):
    """persistent_notification.dismiss via service endpoint."""
    tag = uuid.uuid4().hex[:8]
    nid = f"svc_dismiss_{tag}"

    # Create first
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={"notification_id": nid, "title": "T", "message": "M"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)

    # Dismiss via service
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/dismiss",
        json={"notification_id": nid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_notification_dismiss_all_via_service(rest):
    """persistent_notification.dismiss_all via service endpoint."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/dismiss_all",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Scene service dispatch ───────────────────────────────

async def test_scene_turn_on_via_rest(rest):
    """scene.turn_on via REST service endpoint."""
    await rest.set_state("light.living_room_main", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.evening"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.3)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"
