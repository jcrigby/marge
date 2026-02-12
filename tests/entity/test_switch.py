"""CTS — Switch Entity Tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_switch_turn_on(rest):
    entity_id = "switch.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_switch_turn_off(rest):
    entity_id = "switch.test_off"
    await rest.set_state(entity_id, "on")
    await rest.call_service("switch", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
