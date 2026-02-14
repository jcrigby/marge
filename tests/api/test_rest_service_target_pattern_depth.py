"""
CTS -- REST Service Target Pattern Depth Tests

Tests the REST service dispatch with different entity_id patterns:
string vs array entity_id, target.entity_id pattern, empty entity_id,
and service call with extra data fields.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── String entity_id ──────────────────────────────────────

async def test_service_string_entity_id(rest):
    """Service call with string entity_id works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_str_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Array entity_id ───────────────────────────────────────

async def test_service_array_entity_id(rest):
    """Service call with array entity_id affects all."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.tgt_arr_{i}_{tag}" for i in range(3)]
    for eid in entities:
        await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": entities},
    )
    assert resp.status_code == 200
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Target Pattern ────────────────────────────────────────

async def test_service_target_entity_id(rest):
    """Service call with target.entity_id pattern works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_tgt_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"target": {"entity_id": eid}},
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_service_target_array_entity_id(rest):
    """Service call with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"switch.tgt_tarr_{i}_{tag}" for i in range(2)]
    for eid in entities:
        await rest.set_state(eid, "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_off",
        headers=rest._headers(),
        json={"target": {"entity_id": entities}},
    )
    assert resp.status_code == 200
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "off"


# ── Service with Extra Data ───────────────────────────────

async def test_service_with_brightness_data(rest):
    """Service call passes extra fields as attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_data_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 255,
        "transition": 2,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 255


async def test_service_with_rgb_color(rest):
    """Service call with rgb_color attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_rgb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "rgb_color": [255, 0, 0],
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["rgb_color"] == [255, 0, 0]


# ── Service Response Format ───────────────────────────────

async def test_service_response_has_changed_states(rest):
    """Service response includes changed_states key."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_resp_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    assert "changed_states" in data
    assert isinstance(data["changed_states"], list)


async def test_service_response_contains_entity(rest):
    """Service response changed_states contains the affected entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_resp_e_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    changed_eids = [s["entity_id"] for s in data["changed_states"]]
    assert eid in changed_eids


# ── Empty Body ────────────────────────────────────────────

async def test_service_empty_entity_no_crash(rest):
    """Service call with empty entity_id doesn't crash."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 200
