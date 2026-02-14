"""
CTS -- Climate Temperature Range & On/Off Depth Tests

Tests climate domain: set_temperature with target_temp_high/low,
climate.turn_on, climate.turn_off, and combined attribute scenarios.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Target Temperature Range ───────────────────────────

async def test_climate_set_target_temp_high(rest):
    """climate.set_temperature with target_temp_high."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_high_{tag}"
    await rest.set_state(eid, "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "target_temp_high": 78,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 78


async def test_climate_set_target_temp_low(rest):
    """climate.set_temperature with target_temp_low."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_low_{tag}"
    await rest.set_state(eid, "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "target_temp_low": 65,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_low"] == 65


async def test_climate_set_temp_range_both(rest):
    """climate.set_temperature with both high and low targets."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_both_{tag}"
    await rest.set_state(eid, "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "target_temp_high": 76,
        "target_temp_low": 68,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 76
    assert state["attributes"]["target_temp_low"] == 68


async def test_climate_set_temp_with_range(rest):
    """climate.set_temperature with temp + range."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_all_{tag}"
    await rest.set_state(eid, "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 72,
        "target_temp_high": 76,
        "target_temp_low": 68,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72
    assert state["attributes"]["target_temp_high"] == 76
    assert state["attributes"]["target_temp_low"] == 68


# ── Climate Turn On/Off ────────────────────────────────

async def test_climate_turn_on(rest):
    """climate.turn_on → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("climate", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_climate_turn_off(rest):
    """climate.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_off_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_climate_turn_on_preserves_temp(rest):
    """climate.turn_on preserves temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_ontemp_{tag}"
    await rest.set_state(eid, "off", {"temperature": 70})
    await rest.call_service("climate", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["temperature"] == 70


# ── Full Lifecycle ──────────────────────────────────────

async def test_climate_range_lifecycle(rest):
    """Climate: off → on → set range → set_hvac(auto) → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ctro_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("climate", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "target_temp_high": 78,
        "target_temp_low": 65,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 65

    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "auto",
    })
    assert (await rest.get_state(eid))["state"] == "auto"

    await rest.call_service("climate", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
