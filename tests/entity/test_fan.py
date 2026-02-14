"""
CTS -- Fan Entity Tests

Tests fan domain services: turn_on, turn_off, toggle, set_percentage.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_fan_turn_on(rest):
    """fan.turn_on sets state to 'on'."""
    entity_id = "fan.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("fan", "turn_on", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_fan_turn_off(rest):
    """fan.turn_off sets state to 'off'."""
    entity_id = "fan.test_off"
    await rest.set_state(entity_id, "on", {"percentage": 50})
    await rest.call_service("fan", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_fan_toggle(rest):
    """fan.toggle flips state."""
    entity_id = "fan.test_toggle"
    await rest.set_state(entity_id, "on")
    await rest.call_service("fan", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"

    await rest.call_service("fan", "toggle", {"entity_id": entity_id})
    state2 = await rest.get_state(entity_id)
    assert state2["state"] == "on"


async def test_fan_set_percentage(rest):
    """fan.set_percentage sets speed and turns on."""
    entity_id = "fan.test_pct"
    await rest.set_state(entity_id, "off")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": entity_id,
        "percentage": 75,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_set_percentage_zero(rest):
    """fan.set_percentage to 0 turns off."""
    entity_id = "fan.test_pct_zero"
    await rest.set_state(entity_id, "on", {"percentage": 50})
    await rest.call_service("fan", "set_percentage", {
        "entity_id": entity_id,
        "percentage": 0,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_fan_turn_on_with_percentage(rest):
    """fan.turn_on with percentage data sets both."""
    entity_id = "fan.test_on_pct"
    await rest.set_state(entity_id, "off")
    await rest.call_service("fan", "turn_on", {
        "entity_id": entity_id,
        "percentage": 33,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 33
