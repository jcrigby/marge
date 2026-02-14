"""
CTS -- Switch Entity Tests

Tests switch domain services: turn_on, turn_off, toggle.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_switch_turn_on(rest):
    """switch.turn_on sets state to 'on'."""
    entity_id = "switch.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_switch_turn_off(rest):
    """switch.turn_off sets state to 'off'."""
    entity_id = "switch.test_off"
    await rest.set_state(entity_id, "on")
    await rest.call_service("switch", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_switch_toggle_on_to_off(rest):
    """switch.toggle flips on to off."""
    entity_id = "switch.test_toggle_oo"
    await rest.set_state(entity_id, "on")
    await rest.call_service("switch", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_switch_toggle_off_to_on(rest):
    """switch.toggle flips off to on."""
    entity_id = "switch.test_toggle_fo"
    await rest.set_state(entity_id, "off")
    await rest.call_service("switch", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_switch_preserves_attributes(rest):
    """switch operations preserve entity attributes."""
    entity_id = "switch.test_attr_preserve"
    await rest.set_state(entity_id, "on", {"friendly_name": "Coffee Maker", "icon": "mdi:coffee"})
    await rest.call_service("switch", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == "Coffee Maker"
    assert state["attributes"]["icon"] == "mdi:coffee"
