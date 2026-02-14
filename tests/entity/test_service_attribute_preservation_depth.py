"""
CTS -- Service Attribute Preservation Depth Tests

Tests that service calls correctly preserve existing attributes
when not modifying them, and that service calls that set attributes
properly update them.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Preservation on Toggle ───────────────────────────────

async def test_light_toggle_preserves_brightness(rest):
    """light.toggle preserves brightness attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.sapd_tbr_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200})
    await rest.call_service("light", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 200


async def test_switch_toggle_preserves_attrs(rest):
    """switch.toggle preserves custom attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sapd_sw_{tag}"
    await rest.set_state(eid, "on", {"power_consumption": 150})
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["power_consumption"] == 150


# ── Service Data Sets Attributes ─────────────────────────

async def test_light_turn_on_sets_brightness(rest):
    """light.turn_on with brightness sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.sapd_br_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 128,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 128


async def test_light_turn_on_sets_color_temp(rest):
    """light.turn_on with color_temp sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.sapd_ct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "color_temp": 300,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["color_temp"] == 300


async def test_climate_set_temperature_updates_attr(rest):
    """climate.set_temperature updates temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.sapd_clim_{tag}"
    await rest.set_state(eid, "heat", {"temperature": 70})
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid, "temperature": 75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 75


async def test_climate_set_hvac_preserves_temp(rest):
    """climate.set_hvac_mode preserves temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.sapd_hpres_{tag}"
    await rest.set_state(eid, "heat", {"temperature": 72})
    await rest.call_service("climate", "set_hvac_mode", {
        "entity_id": eid, "hvac_mode": "cool",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "cool"
    assert state["attributes"]["temperature"] == 72


# ── Fan Percentage Attribute ─────────────────────────────

async def test_fan_set_percentage_attr(rest):
    """fan.set_percentage sets percentage and changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.sapd_pct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 75,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_zero_percentage_off(rest):
    """fan.set_percentage with 0 sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.sapd_pct0_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 0,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Lock Attribute Preservation ──────────────────────────

async def test_lock_preserves_attrs_on_lock(rest):
    """lock.lock preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.sapd_lk_{tag}"
    await rest.set_state(eid, "unlocked", {"battery": 85})
    await rest.call_service("lock", "lock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "locked"
    assert state["attributes"]["battery"] == 85


async def test_cover_open_sets_position(rest):
    """cover.open_cover sets current_position to 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.sapd_cov_{tag}"
    await rest.set_state(eid, "closed", {"current_position": 0})
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100
