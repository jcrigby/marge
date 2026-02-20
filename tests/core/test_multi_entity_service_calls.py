"""
CTS -- Multi-Entity Service Call & Array Target Tests

Tests calling services with multiple entity_ids (array pattern),
verifying all entities are affected, and testing edge cases like
empty arrays and mixed domains.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_service_call_array_entity_ids(rest):
    """Service call with entity_id array affects all entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.multi_{tag}_{i}" for i in range(5)]
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


async def test_service_call_single_entity_id_string(rest):
    """Service call with single entity_id string works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.single_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_service_call_returns_changed_states(rest):
    """Service call returns changed entity states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ret_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    data = resp.json()
    changed = data
    assert len(changed) > 0
    assert changed[0]["entity_id"] == eid
    assert changed[0]["state"] == "on"


async def test_service_call_empty_array(rest):
    """Service call with empty entity_id array returns empty result."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": []},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_service_call_preserves_existing_attributes(rest):
    """Service call preserves existing entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pres_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "My Light", "custom": True})

    await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid, "brightness": 200},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200
    assert state["attributes"]["friendly_name"] == "My Light"
    assert state["attributes"]["custom"] is True


async def test_service_call_no_handler_logs_warning(rest):
    """Service call with no handler returns 200 (no state change)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.nohandler_{tag}"
    await rest.set_state(eid, "original")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/sensor/custom_action",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # State should be unchanged (no handler matched)
    state = await rest.get_state(eid)
    assert state["state"] == "original"


async def test_toggle_multiple_entities_mixed_states(rest):
    """Toggle on array with mixed states: each toggles individually."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"switch.mix1_{tag}"
    eid2 = f"switch.mix2_{tag}"
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/switch/toggle",
        json={"entity_id": [eid1, eid2]},
        headers=rest._headers(),
    )

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "off"
    assert s2["state"] == "on"


async def test_service_call_ten_entities(rest):
    """Service call scales to 10 entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.scale_{tag}_{i}" for i in range(10)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eids},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"
