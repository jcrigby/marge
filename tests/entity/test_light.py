"""
CTS — Light Entity Tests (~8 tests)

Tests light domain services: turn_on, turn_off, toggle, brightness, color_temp.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_light_turn_on(rest):
    """light.turn_on sets state to 'on'."""
    entity_id = "light.test_basic"
    await rest.set_state(entity_id, "off")
    await rest.call_service("light", "turn_on", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_light_turn_off(rest):
    """light.turn_off sets state to 'off'."""
    entity_id = "light.test_off"
    await rest.set_state(entity_id, "on")
    await rest.call_service("light", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_light_toggle_on_to_off(rest):
    """light.toggle flips 'on' to 'off'."""
    entity_id = "light.test_toggle"
    await rest.set_state(entity_id, "on")
    await rest.call_service("light", "toggle", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_light_toggle_off_to_on(rest):
    """light.toggle flips 'off' to 'on'."""
    entity_id = "light.test_toggle2"
    await rest.set_state(entity_id, "off")
    await rest.call_service("light", "toggle", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_light_brightness(rest):
    """light.turn_on with brightness sets the brightness attribute."""
    entity_id = "light.test_brightness"
    await rest.set_state(entity_id, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": entity_id,
        "brightness": 128,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 128


async def test_light_color_temp(rest):
    """light.turn_on with color_temp sets the attribute."""
    entity_id = "light.test_color_temp"
    await rest.set_state(entity_id, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": entity_id,
        "color_temp": 400,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
    assert state["attributes"].get("color_temp") == 400


async def test_light_turn_on_multiple(rest):
    """light.turn_on with multiple entity_ids."""
    ids = ["light.test_multi_a", "light.test_multi_b"]
    for eid in ids:
        await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {"entity_id": ids})

    for eid in ids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_light_preserves_attributes_on_off(rest):
    """Turning off a light preserves its attributes."""
    entity_id = "light.test_preserve_attrs"
    await rest.set_state(entity_id, "on", {"brightness": 200, "color_temp": 350})
    await rest.call_service("light", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
    assert state["attributes"].get("brightness") == 200
