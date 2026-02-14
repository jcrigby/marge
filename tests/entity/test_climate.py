"""
CTS -- Climate Entity Tests

Tests climate domain services: set_temperature, set_hvac_mode, set_fan_mode, turn_on, turn_off.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_climate_set_temperature(rest):
    """climate.set_temperature updates the temperature attribute."""
    entity_id = "climate.test_temp"
    await rest.set_state(entity_id, "heat", {"temperature": 66})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": entity_id,
        "temperature": 72,
    })
    state = await rest.get_state(entity_id)
    assert state["attributes"]["temperature"] == 72


async def test_climate_set_hvac_mode(rest):
    """climate.set_hvac_mode changes the state to the mode."""
    entity_id = "climate.test_mode"
    await rest.set_state(entity_id, "heat")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": entity_id,
        "hvac_mode": "cool",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "cool"


async def test_climate_set_hvac_mode_off(rest):
    """climate.set_hvac_mode to 'off' turns off HVAC."""
    entity_id = "climate.test_mode_off"
    await rest.set_state(entity_id, "heat", {"temperature": 70})
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": entity_id,
        "hvac_mode": "off",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
    # Temperature attribute should be preserved
    assert state["attributes"]["temperature"] == 70


async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode updates the fan_mode attribute."""
    entity_id = "climate.test_fan"
    await rest.set_state(entity_id, "cool", {"fan_mode": "auto"})
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": entity_id,
        "fan_mode": "high",
    })
    state = await rest.get_state(entity_id)
    assert state["attributes"]["fan_mode"] == "high"
    # State should be preserved
    assert state["state"] == "cool"


async def test_climate_set_temperature_preserves_mode(rest):
    """climate.set_temperature preserves the current HVAC mode."""
    entity_id = "climate.test_temp_mode"
    await rest.set_state(entity_id, "auto", {"temperature": 68})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": entity_id,
        "temperature": 74,
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "auto"
    assert state["attributes"]["temperature"] == 74


async def test_climate_set_temperature_with_high_low(rest):
    """climate.set_temperature supports target_temp_high and target_temp_low."""
    entity_id = "climate.test_temp_range"
    await rest.set_state(entity_id, "heat_cool", {"temperature": 70})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": entity_id,
        "target_temp_high": 78,
        "target_temp_low": 65,
    })
    state = await rest.get_state(entity_id)
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 65


async def test_climate_turn_on_via_generic(rest):
    """climate domain supports generic turn_on via fallback."""
    entity_id = "climate.test_generic_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("climate", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_climate_turn_off_via_generic(rest):
    """climate domain supports generic turn_off via fallback."""
    entity_id = "climate.test_generic_off"
    await rest.set_state(entity_id, "heat")
    await rest.call_service("climate", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"
