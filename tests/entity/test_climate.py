"""CTS — Climate Entity Tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_climate_set_temperature(rest):
    entity_id = "climate.test_temp"
    await rest.set_state(entity_id, "heat", {"temperature": 66})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": entity_id,
        "temperature": 72,
    })
    state = await rest.get_state(entity_id)
    assert state["attributes"]["temperature"] == 72


async def test_climate_set_hvac_mode(rest):
    entity_id = "climate.test_mode"
    await rest.set_state(entity_id, "heat")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": entity_id,
        "hvac_mode": "cool",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "cool"
