"""
CTS -- REST Service Call with Entity Arrays Tests

Tests service call dispatch with entity_id arrays (multiple targets),
target pattern, and cross-domain service calls via REST API.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_entity_id_array_turn_on(rest):
    """Service call with entity_id array turns on all."""
    for i in range(3):
        await rest.set_state(f"light.arr_on_{i}", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": ["light.arr_on_0", "light.arr_on_1", "light.arr_on_2"]},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3

    for i in range(3):
        state = await rest.get_state(f"light.arr_on_{i}")
        assert state["state"] == "on"


async def test_entity_id_array_turn_off(rest):
    """Service call with entity_id array turns off all."""
    for i in range(2):
        await rest.set_state(f"switch.arr_off_{i}", "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_off",
        json={"entity_id": ["switch.arr_off_0", "switch.arr_off_1"]},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_target_entity_id_pattern(rest):
    """Service call with target.entity_id pattern works."""
    await rest.set_state("light.arr_target", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"target": {"entity_id": "light.arr_target"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state("light.arr_target")
    assert state["state"] == "on"


async def test_target_entity_id_array_pattern(rest):
    """Service call with target.entity_id array pattern works."""
    for i in range(2):
        await rest.set_state(f"light.arr_ta_{i}", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"target": {"entity_id": ["light.arr_ta_0", "light.arr_ta_1"]}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for i in range(2):
        state = await rest.get_state(f"light.arr_ta_{i}")
        assert state["state"] == "on"


async def test_service_with_data_array(rest):
    """Service call with entity array passes data to all."""
    for i in range(2):
        await rest.set_state(f"light.arr_data_{i}", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={
            "entity_id": ["light.arr_data_0", "light.arr_data_1"],
            "brightness": 200,
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for i in range(2):
        state = await rest.get_state(f"light.arr_data_{i}")
        assert state["state"] == "on"
        assert state["attributes"]["brightness"] == 200


async def test_service_changed_states_all_fields(rest):
    """Changed states from array call have all required fields."""
    await rest.set_state("light.arr_fields_1", "off")
    await rest.set_state("light.arr_fields_2", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": ["light.arr_fields_1", "light.arr_fields_2"]},
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "entity_id" in entry
        assert "state" in entry
        assert "attributes" in entry
        assert "last_changed" in entry
        assert "last_updated" in entry
        assert "context" in entry


async def test_homeassistant_turn_on_array(rest):
    """homeassistant.turn_on with entity array."""
    await rest.set_state("light.arr_ha_1", "off")
    await rest.set_state("switch.arr_ha_2", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/homeassistant/turn_on",
        json={"entity_id": ["light.arr_ha_1", "switch.arr_ha_2"]},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    s1 = await rest.get_state("light.arr_ha_1")
    s2 = await rest.get_state("switch.arr_ha_2")
    assert s1["state"] == "on"
    assert s2["state"] == "on"


async def test_toggle_array(rest):
    """Toggle with entity array flips all states."""
    await rest.set_state("switch.arr_tog_1", "on")
    await rest.set_state("switch.arr_tog_2", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/toggle",
        json={"entity_id": ["switch.arr_tog_1", "switch.arr_tog_2"]},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    s1 = await rest.get_state("switch.arr_tog_1")
    s2 = await rest.get_state("switch.arr_tog_2")
    assert s1["state"] == "off"
    assert s2["state"] == "on"
