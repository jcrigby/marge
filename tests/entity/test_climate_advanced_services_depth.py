"""
CTS -- Climate Advanced Services Depth Tests

Tests climate domain service handlers: set_hvac_mode, set_temperature,
set_fan_mode, set_preset_mode, set_swing_mode, and attribute
preservation across mode changes.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── HVAC Mode ────────────────────────────────────────────

async def test_climate_set_hvac_heat(rest):
    """climate.set_hvac_mode to heat."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_heat_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "heat",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "heat"


async def test_climate_set_hvac_cool(rest):
    """climate.set_hvac_mode to cool."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_cool_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "cool",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_climate_set_hvac_auto(rest):
    """climate.set_hvac_mode to auto."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_auto_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "auto"


# ── Temperature ──────────────────────────────────────────

async def test_climate_set_temperature(rest):
    """climate.set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_temp_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 72,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


async def test_climate_temperature_preserves_mode(rest):
    """climate.set_temperature preserves HVAC mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_tpres_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 68,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"


# ── Fan Mode ─────────────────────────────────────────────

async def test_climate_set_fan_mode(rest):
    """climate.set_fan_mode sets fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_fan_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "high",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "high"


async def test_climate_set_fan_mode_auto(rest):
    """climate.set_fan_mode to auto."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_fana_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["fan_mode"] == "auto"


# ── Preset Mode ──────────────────────────────────────────

async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_pre_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "eco",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "eco"


# ── Swing Mode ───────────────────────────────────────────

async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode sets swing_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_swg_{tag}"
    await rest.set_state(eid, "cool")
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid, "swing_mode": "vertical",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["swing_mode"] == "vertical"


# ── Full Lifecycle ───────────────────────────────────────

async def test_climate_full_lifecycle(rest):
    """Climate: off → heat+temp → cool → set_fan → set_preset."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.casd_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "heat",
    })
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 72,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "heat"
    assert state["attributes"]["temperature"] == 72

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "cool",
    })
    assert (await rest.get_state(eid))["state"] == "cool"

    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid, "fan_mode": "low",
    })
    assert (await rest.get_state(eid))["attributes"]["fan_mode"] == "low"
