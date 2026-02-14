"""
CTS -- Climate Service Handler Depth Tests

Tests climate domain service handlers: set_temperature, set_hvac_mode,
set_fan_mode, set_preset_mode, set_swing_mode, turn_on, turn_off.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_set_temperature(rest):
    """set_temperature stores temperature attribute."""
    await rest.set_state("climate.depth_temp", "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.depth_temp",
        "temperature": 72,
    })
    state = await rest.get_state("climate.depth_temp")
    assert state["attributes"]["temperature"] == 72
    assert state["state"] == "heat"


async def test_set_temperature_high_low(rest):
    """set_temperature stores target_temp_high and target_temp_low."""
    await rest.set_state("climate.depth_hl", "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.depth_hl",
        "target_temp_high": 78,
        "target_temp_low": 68,
    })
    state = await rest.get_state("climate.depth_hl")
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 68


async def test_set_hvac_mode(rest):
    """set_hvac_mode changes state to the mode value."""
    await rest.set_state("climate.depth_hvac", "off")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": "climate.depth_hvac",
        "hvac_mode": "cool",
    })
    state = await rest.get_state("climate.depth_hvac")
    assert state["state"] == "cool"


async def test_set_fan_mode(rest):
    """set_fan_mode stores fan_mode attribute."""
    await rest.set_state("climate.depth_fan", "heat")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": "climate.depth_fan",
        "fan_mode": "high",
    })
    state = await rest.get_state("climate.depth_fan")
    assert state["attributes"]["fan_mode"] == "high"


async def test_set_preset_mode(rest):
    """set_preset_mode stores preset_mode attribute."""
    await rest.set_state("climate.depth_preset", "auto")
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": "climate.depth_preset",
        "preset_mode": "away",
    })
    state = await rest.get_state("climate.depth_preset")
    assert state["attributes"]["preset_mode"] == "away"


async def test_set_swing_mode(rest):
    """set_swing_mode stores swing_mode attribute."""
    await rest.set_state("climate.depth_swing", "cool")
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": "climate.depth_swing",
        "swing_mode": "vertical",
    })
    state = await rest.get_state("climate.depth_swing")
    assert state["attributes"]["swing_mode"] == "vertical"


async def test_climate_turn_on(rest):
    """turn_on sets state to on."""
    await rest.set_state("climate.depth_on", "off")
    await rest.call_service("climate", "turn_on", {"entity_id": "climate.depth_on"})
    state = await rest.get_state("climate.depth_on")
    assert state["state"] == "on"


async def test_climate_turn_off(rest):
    """turn_off sets state to off."""
    await rest.set_state("climate.depth_off", "heat")
    await rest.call_service("climate", "turn_off", {"entity_id": "climate.depth_off"})
    state = await rest.get_state("climate.depth_off")
    assert state["state"] == "off"


async def test_set_temperature_preserves_attrs(rest):
    """set_temperature preserves existing attributes."""
    await rest.set_state("climate.depth_pres", "heat", {"fan_mode": "low"})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.depth_pres",
        "temperature": 75,
    })
    state = await rest.get_state("climate.depth_pres")
    assert state["attributes"]["temperature"] == 75
    assert state["attributes"]["fan_mode"] == "low"
