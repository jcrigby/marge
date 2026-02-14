"""
CTS -- Entity Lifecycle Depth Tests

Tests entity create/read/update/delete lifecycle with various
entity types, attribute evolution, and state transitions.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_with_attrs(rest):
    """Create entity with attributes."""
    await rest.set_state("sensor.lifecycle_create", "100", {
        "unit": "kWh",
        "friendly_name": "Lifecycle Test",
    })
    state = await rest.get_state("sensor.lifecycle_create")
    assert state["state"] == "100"
    assert state["attributes"]["unit"] == "kWh"
    assert state["attributes"]["friendly_name"] == "Lifecycle Test"


async def test_update_state_preserves_attrs_via_service(rest):
    """Service call preserves existing attributes."""
    await rest.set_state("light.lifecycle_pres", "off", {"brightness": 100})
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.lifecycle_pres",
    })
    state = await rest.get_state("light.lifecycle_pres")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 100


async def test_update_attrs_via_set_state(rest):
    """Updating via set_state replaces attributes."""
    await rest.set_state("sensor.lifecycle_upd", "50", {"unit": "C"})
    await rest.set_state("sensor.lifecycle_upd", "60", {"unit": "F", "precision": 1})
    state = await rest.get_state("sensor.lifecycle_upd")
    assert state["state"] == "60"
    assert state["attributes"]["unit"] == "F"
    assert state["attributes"]["precision"] == 1


async def test_delete_entity(rest):
    """Deleting entity makes it unavailable."""
    await rest.set_state("sensor.lifecycle_del", "temp")
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.lifecycle_del",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state("sensor.lifecycle_del")
    assert state is None


async def test_recreate_after_delete(rest):
    """Entity can be recreated after deletion."""
    await rest.set_state("sensor.lifecycle_recreate", "first")
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.lifecycle_recreate",
        headers=rest._headers(),
    )
    await rest.set_state("sensor.lifecycle_recreate", "second")
    state = await rest.get_state("sensor.lifecycle_recreate")
    assert state["state"] == "second"


async def test_entity_id_with_numbers(rest):
    """Entity IDs with numbers work correctly."""
    await rest.set_state("sensor.room_123_temp_456", "21.5")
    state = await rest.get_state("sensor.room_123_temp_456")
    assert state["state"] == "21.5"


async def test_entity_id_with_underscores(rest):
    """Entity IDs with multiple underscores."""
    await rest.set_state("sensor.very_long_entity_name_test", "ok")
    state = await rest.get_state("sensor.very_long_entity_name_test")
    assert state["state"] == "ok"


async def test_state_value_special_chars(rest):
    """State value with special characters."""
    await rest.set_state("sensor.lifecycle_special", "72°F / 22.2°C")
    state = await rest.get_state("sensor.lifecycle_special")
    assert state["state"] == "72°F / 22.2°C"


async def test_state_value_numeric_string(rest):
    """Numeric state values stored as strings."""
    await rest.set_state("sensor.lifecycle_num", "3.14159")
    state = await rest.get_state("sensor.lifecycle_num")
    assert state["state"] == "3.14159"


async def test_attribute_nested_object(rest):
    """Attributes can contain nested objects."""
    await rest.set_state("sensor.lifecycle_nested", "ok", {
        "config": {"threshold": 50, "enabled": True},
    })
    state = await rest.get_state("sensor.lifecycle_nested")
    assert state["attributes"]["config"]["threshold"] == 50
    assert state["attributes"]["config"]["enabled"] is True


async def test_attribute_array_value(rest):
    """Attributes can contain arrays."""
    await rest.set_state("sensor.lifecycle_arr", "ok", {
        "targets": [1, 2, 3],
    })
    state = await rest.get_state("sensor.lifecycle_arr")
    assert state["attributes"]["targets"] == [1, 2, 3]


async def test_multiple_domain_lifecycle(rest):
    """Different domains have independent lifecycles."""
    await rest.set_state("sensor.lifecycle_dom", "42")
    await rest.set_state("light.lifecycle_dom", "on")
    await rest.set_state("switch.lifecycle_dom", "off")

    s1 = await rest.get_state("sensor.lifecycle_dom")
    s2 = await rest.get_state("light.lifecycle_dom")
    s3 = await rest.get_state("switch.lifecycle_dom")

    assert s1["state"] == "42"
    assert s2["state"] == "on"
    assert s3["state"] == "off"
