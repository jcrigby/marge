"""
CTS -- Climate HVAC Mode and Attribute Depth Tests

Tests all climate services: set_temperature (single + high/low range),
set_hvac_mode, set_fan_mode, set_preset_mode, set_swing_mode.
Verifies state transitions and attribute passthrough.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── set_temperature ────────────────────────────────────────

async def test_climate_set_temperature(rest):
    """climate.set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 72
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


async def test_climate_set_temperature_preserves_state(rest):
    """climate.set_temperature preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_ps_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 68
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_climate_set_temperature_range(rest):
    """climate.set_temperature with target_temp_high and target_temp_low."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_range_{tag}"
    await rest.set_state(eid, "heat_cool")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "target_temp_high": 78,
        "target_temp_low": 65,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 65


# ── set_hvac_mode ──────────────────────────────────────────

async def test_climate_set_hvac_heat(rest):
    """climate.set_hvac_mode to heat changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_mode_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "heat"
    })
    assert (await rest.get_state(eid))["state"] == "heat"


async def test_climate_set_hvac_cool(rest):
    """climate.set_hvac_mode to cool changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_cool_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "cool"
    })
    assert (await rest.get_state(eid))["state"] == "cool"


async def test_climate_set_hvac_off(rest):
    """climate.set_hvac_mode to off changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.hvac_off_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "off"
    })
    assert (await rest.get_state(eid))["state"] == "off"


# ── set_fan_mode ───────────────────────────────────────────

async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode sets fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.fan_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "high"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "high"


async def test_climate_set_fan_auto(rest):
    """climate.set_fan_mode to auto."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.fan_auto_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "auto"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "auto"


# ── set_preset_mode ────────────────────────────────────────

async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.preset_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "away"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "away"


# ── set_swing_mode ─────────────────────────────────────────

async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode sets swing_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.swing_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid, "swing_mode": "vertical"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["swing_mode"] == "vertical"


# ── Combined attribute preservation ────────────────────────

async def test_climate_preserves_existing_attrs(rest):
    """Climate services preserve existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.preserve_{tag}"
    await rest.set_state(eid, "heat", {
        "friendly_name": "Living Room",
        "temperature": 72,
        "fan_mode": "auto",
    })
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "eco"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == "Living Room"
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["preset_mode"] == "eco"
