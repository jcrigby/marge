"""
CTS -- Water Heater and Humidifier Service Depth Tests

Tests water_heater (set_temperature, set_operation_mode, turn_on,
turn_off) and humidifier (turn_on, turn_off, toggle, set_humidity,
set_mode) service handlers.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Water Heater ─────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whhd_temp_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 120,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode sets state to mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whhd_mode_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid, "operation_mode": "performance",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "performance"


async def test_water_heater_turn_on(rest):
    """water_heater.turn_on sets state to eco."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whhd_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("water_heater", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whhd_off_{tag}"
    await rest.set_state(eid, "eco")
    await rest.call_service("water_heater", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_water_heater_temp_preserves_state(rest):
    """water_heater.set_temperature preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.whhd_pres_{tag}"
    await rest.set_state(eid, "performance")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 130,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "performance"
    assert state["attributes"]["temperature"] == 130


# ── Humidifier ───────────────────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_hon_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_hoff_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_humidifier_toggle_on_to_off(rest):
    """humidifier.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_htog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_humidifier_toggle_off_to_on(rest):
    """humidifier.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_htog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity sets humidity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_hum_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 45,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["humidity"] == 45


async def test_humidifier_set_mode(rest):
    """humidifier.set_mode sets mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.whhd_hmode_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "auto",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["mode"] == "auto"
