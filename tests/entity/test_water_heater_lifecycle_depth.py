"""
CTS -- Water Heater Lifecycle Depth Tests

Tests water_heater domain services: set_temperature,
set_operation_mode, turn_on, turn_off, and full lifecycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Set Temperature ─────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_temp_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 120,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_temperature_preserves_state(rest):
    """water_heater.set_temperature preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_tpres_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 140,
    })
    assert (await rest.get_state(eid))["state"] == "eco"


# ── Set Operation Mode ──────────────────────────────────

async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_mode_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid, "operation_mode": "performance",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "performance"


# ── Turn On/Off ─────────────────────────────────────────

async def test_water_heater_turn_on(rest):
    """water_heater.turn_on → eco."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("water_heater", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_off_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


# ── Attribute Preservation ──────────────────────────────

async def test_water_heater_mode_preserves_temp(rest):
    """Operation mode change preserves temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_mpres_{tag}"
    await rest.set_state(eid, "eco", {"temperature": 120})
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid, "operation_mode": "performance",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "performance"
    assert state["attributes"]["temperature"] == 120


# ── Full Lifecycle ──────────────────────────────────────

async def test_water_heater_full_lifecycle(rest):
    """Water heater: off → on → set_temp → set_mode → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whld_lc_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("water_heater", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "eco"

    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 130,
    })
    assert (await rest.get_state(eid))["attributes"]["temperature"] == 130

    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid, "operation_mode": "performance",
    })
    assert (await rest.get_state(eid))["state"] == "performance"

    await rest.call_service("water_heater", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
