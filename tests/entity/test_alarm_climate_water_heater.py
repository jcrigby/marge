"""
CTS -- Alarm, Climate, and Water Heater Service Depth Tests

Tests alarm_control_panel arm/disarm/trigger, climate preset modes
and fan modes, and water_heater operation modes and temperature.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Alarm Control Panel ──────────────────────────────────

async def test_arm_home(rest):
    """Alarm arm_home sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ah_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_home"


async def test_arm_away(rest):
    """Alarm arm_away sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.aa_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_away"


async def test_arm_night(rest):
    """Alarm arm_night sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.an_{tag}"
    await rest.set_state(eid, "disarmed")

    await rest.call_service("alarm_control_panel", "arm_night", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "armed_night"


async def test_disarm(rest):
    """Alarm disarm sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.ad_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "disarmed"


async def test_trigger(rest):
    """Alarm trigger sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.at_{tag}"
    await rest.set_state(eid, "armed_home")

    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "triggered"


# ── Climate ──────────────────────────────────────────────

async def test_climate_set_fan_mode(rest):
    """Climate set_fan_mode stores fan_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.fm_{tag}"
    await rest.set_state(eid, "cool")

    await rest.call_service("climate", "set_fan_mode", {
        "entity_id": eid,
        "fan_mode": "high",
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("fan_mode") == "high"


async def test_climate_set_preset_mode(rest):
    """Climate set_preset_mode stores preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.pm_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": eid,
        "preset_mode": "eco",
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("preset_mode") == "eco"


async def test_climate_set_swing_mode(rest):
    """Climate set_swing_mode stores swing_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.sm_{tag}"
    await rest.set_state(eid, "cool")

    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": eid,
        "swing_mode": "vertical",
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("swing_mode") == "vertical"


async def test_climate_set_temperature_stores_attr(rest):
    """Climate set_temperature stores temperature and target_temp_high/low."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.tattr_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 68,
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("temperature") == 68


async def test_climate_turn_off(rest):
    """Climate turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.off_{tag}"
    await rest.set_state(eid, "heat")

    await rest.call_service("climate", "turn_off", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Water Heater ─────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """Water heater set_temperature stores temperature."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.temp_{tag}"
    await rest.set_state(eid, "eco")

    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid,
        "temperature": 120,
    })

    state = await rest.get_state(eid)
    assert state["attributes"].get("temperature") == 120


async def test_water_heater_set_operation_mode(rest):
    """Water heater set_operation_mode changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.op_{tag}"
    await rest.set_state(eid, "eco")

    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid,
        "operation_mode": "performance",
    })

    state = await rest.get_state(eid)
    assert state["state"] == "performance"


async def test_water_heater_turn_on(rest):
    """Water heater turn_on sets state to eco."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.on_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("water_heater", "turn_on", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """Water heater turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.woff_{tag}"
    await rest.set_state(eid, "eco")

    await rest.call_service("water_heater", "turn_off", {
        "entity_id": eid,
    })

    state = await rest.get_state(eid)
    assert state["state"] == "off"
