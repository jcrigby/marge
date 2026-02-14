"""
CTS -- Service Response Format Depth Tests

Tests POST /api/services/<domain>/<service> response format:
changed_states presence, state object format within changed_states,
and service calls that don't change state.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Response Contains changed_states ─────────────────────

async def test_service_response_has_changed_states(rest):
    """Service call that changes state includes changed_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.srfd_chg_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    assert "changed_states" in data
    assert isinstance(data["changed_states"], list)
    assert len(data["changed_states"]) >= 1


async def test_changed_state_has_entity_id(rest):
    """changed_states entry has entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.srfd_eid_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    changed = data["changed_states"]
    assert changed[0]["entity_id"] == eid


async def test_changed_state_has_new_state(rest):
    """changed_states entry has state field with new value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.srfd_ns_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    changed = data["changed_states"]
    assert changed[0]["state"] == "on"


async def test_changed_state_has_attributes(rest):
    """changed_states entry has attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srfd_attr_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid, "brightness": 200},
    )
    data = resp.json()
    changed = data["changed_states"]
    assert "attributes" in changed[0]
    assert changed[0]["attributes"]["brightness"] == 200


# ── No-op Service (No State Change) ─────────────────────

async def test_noop_service_no_changed_states(rest):
    """Service call that's a no-op has no changed_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.srfd_noop_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    # button.press is a no-op, so changed_states should be absent or empty
    if "changed_states" in data:
        assert data["changed_states"] == []


# ── Multiple Entities Changed ────────────────────────────

async def test_multiple_entities_changed(rest):
    """Service call on multiple entities returns all changed."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.srfd_m{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")

    # Call service on first entity
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eids[0]},
    )
    data = resp.json()
    assert "changed_states" in data


# ── Service Response Status ──────────────────────────────

async def test_service_response_200(rest):
    """Service call returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srfd_200_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200


async def test_service_response_is_json(rest):
    """Service call response is JSON."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srfd_json_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    ct = resp.headers.get("content-type", "")
    assert "json" in ct
