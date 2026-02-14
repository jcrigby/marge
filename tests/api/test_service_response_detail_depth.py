"""
CTS -- Service Response Detail Depth Tests

Tests the service call response format in depth: the changed_states
array content, entity state fields within the response, empty
changed_states for special-case services, and multi-entity responses.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── changed_states Entity Fields ────────────────────────────

async def test_changed_states_entity_has_entity_id(rest):
    """Service response changed_states entry has entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_eid_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    assert len(changed) >= 1
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert entry["entity_id"] == eid


async def test_changed_states_entity_has_state(rest):
    """Service response changed_states entry has updated state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.srd_state_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert entry["state"] == "on"


async def test_changed_states_entity_has_attributes(rest):
    """Service response changed_states entry has attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_attr_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "Test Light"})
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid, "brightness": 200},
    )
    changed = resp.json()["changed_states"]
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert "attributes" in entry
    assert entry["attributes"]["brightness"] == 200


async def test_changed_states_entity_has_last_changed(rest):
    """Service response changed_states entry has last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_lc_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert "last_changed" in entry
    assert "T" in entry["last_changed"]


async def test_changed_states_entity_has_context(rest):
    """Service response changed_states entry has context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_ctx_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert "context" in entry
    assert "id" in entry["context"]


# ── Multiple Entities ──────────────────────────────────────

async def test_changed_states_multiple_entities(rest):
    """Service call with multiple entity_ids returns all in changed_states."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.srd_multi_{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eids},
    )
    changed = resp.json()["changed_states"]
    changed_eids = {e["entity_id"] for e in changed}
    for eid in eids:
        assert eid in changed_eids


async def test_changed_states_matches_get_state(rest):
    """Entity in changed_states matches subsequent GET /api/states/{id}."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_match_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid, "brightness": 150},
    )
    changed = resp.json()["changed_states"]
    resp_entity = next(e for e in changed if e["entity_id"] == eid)
    get_entity = await rest.get_state(eid)
    assert resp_entity["state"] == get_entity["state"]
    assert resp_entity["attributes"]["brightness"] == get_entity["attributes"]["brightness"]


# ── Special-Case Services Return Empty changed_states ──────

async def test_notification_service_no_changed(rest):
    """persistent_notification.create omits changed_states (empty)."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        headers=rest._headers(),
        json={
            "notification_id": f"srd_{tag}",
            "title": "Test",
            "message": "Body",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # changed_states is skip_serializing_if empty — field absent or empty
    assert data.get("changed_states", []) == []


async def test_scene_service_no_changed(rest):
    """scene.turn_on omits changed_states (empty)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        headers=rest._headers(),
        json={"entity_id": "scene.nonexistent"},
    )
    assert resp.status_code == 200
    assert resp.json().get("changed_states", []) == []


async def test_automation_service_no_changed(rest):
    """automation.trigger omits changed_states (empty)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        headers=rest._headers(),
        json={"entity_id": "automation.nonexistent"},
    )
    assert resp.status_code == 200
    assert resp.json().get("changed_states", []) == []


# ── Toggle Response Shows Toggled State ────────────────────

async def test_toggle_response_shows_new_state(rest):
    """Toggle response changed_states shows the post-toggle state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.srd_tog_{tag}"
    await rest.set_state(eid, "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/toggle",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    entry = next(e for e in changed if e["entity_id"] == eid)
    assert entry["state"] == "off"


# ── Service on New Entity ──────────────────────────────────

async def test_service_on_new_entity_in_changed(rest):
    """Service on non-existent entity creates it and shows in changed_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srd_new_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    changed = resp.json()["changed_states"]
    changed_eids = {e["entity_id"] for e in changed}
    assert eid in changed_eids
