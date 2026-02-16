"""
CTS -- Domain Toggle and State Transition Tests

Tests toggle semantics across all toggleable domains, light/switch
service operations, and verifies correct state transitions for
various service calls.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Light Services ───────────────────────────────────────

async def test_light_turn_on(rest):
    """light.turn_on sets state to 'on'."""
    await rest.set_state("light.dt_lt_on", "off")
    await rest.call_service("light", "turn_on", {"entity_id": "light.dt_lt_on"})
    state = await rest.get_state("light.dt_lt_on")
    assert state["state"] == "on"


async def test_light_turn_off(rest):
    """light.turn_off sets state to 'off'."""
    await rest.set_state("light.dt_lt_off", "on")
    await rest.call_service("light", "turn_off", {"entity_id": "light.dt_lt_off"})
    state = await rest.get_state("light.dt_lt_off")
    assert state["state"] == "off"


@pytest.mark.parametrize("attr,value", [
    ("brightness", 128),
    ("color_temp", 400),
])
async def test_light_turn_on_with_attribute(rest, attr, value):
    """light.turn_on with brightness/color_temp sets the attribute."""
    eid = f"light.dt_lt_{attr}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        attr: value,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get(attr) == value


async def test_light_turn_on_multiple(rest):
    """light.turn_on with multiple entity_ids."""
    ids = ["light.dt_lt_multi_a", "light.dt_lt_multi_b"]
    for eid in ids:
        await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": ids})
    for eid in ids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_light_preserves_attributes_on_off(rest):
    """Turning off a light preserves its attributes."""
    await rest.set_state("light.dt_lt_preserve", "on", {"brightness": 200, "color_temp": 350})
    await rest.call_service("light", "turn_off", {"entity_id": "light.dt_lt_preserve"})
    state = await rest.get_state("light.dt_lt_preserve")
    assert state["state"] == "off"
    assert state["attributes"].get("brightness") == 200


# ── Switch Services ──────────────────────────────────────

async def test_switch_turn_on(rest):
    """switch.turn_on sets state to 'on'."""
    await rest.set_state("switch.dt_sw_on", "off")
    await rest.call_service("switch", "turn_on", {"entity_id": "switch.dt_sw_on"})
    state = await rest.get_state("switch.dt_sw_on")
    assert state["state"] == "on"


async def test_switch_turn_off(rest):
    """switch.turn_off sets state to 'off'."""
    await rest.set_state("switch.dt_sw_off", "on")
    await rest.call_service("switch", "turn_off", {"entity_id": "switch.dt_sw_off"})
    state = await rest.get_state("switch.dt_sw_off")
    assert state["state"] == "off"


async def test_switch_toggle_on_to_off(rest):
    """switch.toggle from on goes to off."""
    await rest.set_state("switch.dt_sw1", "on")
    await rest.call_service("switch", "toggle", {"entity_id": "switch.dt_sw1"})
    state = await rest.get_state("switch.dt_sw1")
    assert state["state"] == "off"


async def test_switch_toggle_off_to_on(rest):
    """switch.toggle from off goes to on."""
    await rest.set_state("switch.dt_sw2", "off")
    await rest.call_service("switch", "toggle", {"entity_id": "switch.dt_sw2"})
    state = await rest.get_state("switch.dt_sw2")
    assert state["state"] == "on"


async def test_switch_preserves_attributes(rest):
    """switch operations preserve entity attributes."""
    await rest.set_state("switch.dt_sw_attrs", "on", {"friendly_name": "Coffee Maker", "icon": "mdi:coffee"})
    await rest.call_service("switch", "turn_off", {"entity_id": "switch.dt_sw_attrs"})
    state = await rest.get_state("switch.dt_sw_attrs")
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == "Coffee Maker"
    assert state["attributes"]["icon"] == "mdi:coffee"


# ── Input Boolean Toggle ────────────────────────────────

async def test_input_boolean_turn_on(rest):
    """input_boolean.turn_on sets on."""
    await rest.set_state("input_boolean.dt_ib1", "off")
    await rest.call_service("input_boolean", "turn_on", {"entity_id": "input_boolean.dt_ib1"})
    state = await rest.get_state("input_boolean.dt_ib1")
    assert state["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean.turn_off sets off."""
    await rest.set_state("input_boolean.dt_ib2", "on")
    await rest.call_service("input_boolean", "turn_off", {"entity_id": "input_boolean.dt_ib2"})
    state = await rest.get_state("input_boolean.dt_ib2")
    assert state["state"] == "off"


# ── Siren Toggle ────────────────────────────────────────

async def test_siren_toggle_on_to_off(rest):
    """siren.toggle from on goes to off."""
    await rest.set_state("siren.dt_sir1", "on")
    await rest.call_service("siren", "toggle", {"entity_id": "siren.dt_sir1"})
    state = await rest.get_state("siren.dt_sir1")
    assert state["state"] == "off"


async def test_siren_toggle_off_to_on(rest):
    """siren.toggle from off goes to on."""
    await rest.set_state("siren.dt_sir2", "off")
    await rest.call_service("siren", "toggle", {"entity_id": "siren.dt_sir2"})
    state = await rest.get_state("siren.dt_sir2")
    assert state["state"] == "on"


# ── Valve Toggle ─────────────────────────────────────────

async def test_valve_toggle_open_to_closed(rest):
    """valve.toggle from open goes to closed."""
    await rest.set_state("valve.dt_v1", "open")
    await rest.call_service("valve", "toggle", {"entity_id": "valve.dt_v1"})
    state = await rest.get_state("valve.dt_v1")
    assert state["state"] == "closed"


async def test_valve_toggle_closed_to_open(rest):
    """valve.toggle from closed goes to open."""
    await rest.set_state("valve.dt_v2", "closed")
    await rest.call_service("valve", "toggle", {"entity_id": "valve.dt_v2"})
    state = await rest.get_state("valve.dt_v2")
    assert state["state"] == "open"


# ── Fan Toggle ──────────────────────────────────────────

async def test_fan_toggle_on_to_off(rest):
    """fan.toggle from on goes to off."""
    await rest.set_state("fan.dt_fan1", "on")
    await rest.call_service("fan", "toggle", {"entity_id": "fan.dt_fan1"})
    state = await rest.get_state("fan.dt_fan1")
    assert state["state"] == "off"


async def test_fan_toggle_off_to_on(rest):
    """fan.toggle from off goes to on."""
    await rest.set_state("fan.dt_fan2", "off")
    await rest.call_service("fan", "toggle", {"entity_id": "fan.dt_fan2"})
    state = await rest.get_state("fan.dt_fan2")
    assert state["state"] == "on"


# ── Homeassistant Toggle ────────────────────────────────

async def test_homeassistant_toggle_on_to_off(rest):
    """homeassistant.toggle from on goes to off."""
    await rest.set_state("light.dt_ha1", "on")
    await rest.call_service("homeassistant", "toggle", {"entity_id": "light.dt_ha1"})
    state = await rest.get_state("light.dt_ha1")
    assert state["state"] == "off"


async def test_homeassistant_toggle_off_to_on(rest):
    """homeassistant.toggle from off goes to on."""
    await rest.set_state("switch.dt_ha2", "off")
    await rest.call_service("homeassistant", "toggle", {"entity_id": "switch.dt_ha2"})
    state = await rest.get_state("switch.dt_ha2")
    assert state["state"] == "on"


async def test_homeassistant_turn_on_any(rest):
    """homeassistant.turn_on works across domains."""
    await rest.set_state("sensor.dt_ha_on", "off")
    await rest.call_service("homeassistant", "turn_on", {"entity_id": "sensor.dt_ha_on"})
    state = await rest.get_state("sensor.dt_ha_on")
    assert state["state"] == "on"


async def test_homeassistant_turn_off_any(rest):
    """homeassistant.turn_off works across domains."""
    await rest.set_state("sensor.dt_ha_off", "on")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": "sensor.dt_ha_off"})
    state = await rest.get_state("sensor.dt_ha_off")
    assert state["state"] == "off"


# ── Humidifier Toggle ───────────────────────────────────

async def test_humidifier_toggle_on_to_off(rest):
    """humidifier.toggle from on goes to off."""
    await rest.set_state("humidifier.dt_hum1", "on")
    await rest.call_service("humidifier", "toggle", {"entity_id": "humidifier.dt_hum1"})
    state = await rest.get_state("humidifier.dt_hum1")
    assert state["state"] == "off"


async def test_humidifier_toggle_off_to_on(rest):
    """humidifier.toggle from off goes to on."""
    await rest.set_state("humidifier.dt_hum2", "off")
    await rest.call_service("humidifier", "toggle", {"entity_id": "humidifier.dt_hum2"})
    state = await rest.get_state("humidifier.dt_hum2")
    assert state["state"] == "on"


# ── Alarm Control Panel Transitions ─────────────────────

async def test_alarm_arm_home(rest):
    """alarm_control_panel.arm_home sets armed_home."""
    await rest.set_state("alarm_control_panel.dt_alarm", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_home", {
        "entity_id": "alarm_control_panel.dt_alarm",
    })
    state = await rest.get_state("alarm_control_panel.dt_alarm")
    assert state["state"] == "armed_home"


async def test_alarm_arm_away(rest):
    """alarm_control_panel.arm_away sets armed_away."""
    await rest.set_state("alarm_control_panel.dt_alarm2", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_away", {
        "entity_id": "alarm_control_panel.dt_alarm2",
    })
    state = await rest.get_state("alarm_control_panel.dt_alarm2")
    assert state["state"] == "armed_away"


async def test_alarm_arm_night(rest):
    """alarm_control_panel.arm_night sets armed_night."""
    await rest.set_state("alarm_control_panel.dt_alarm3", "disarmed")
    await rest.call_service("alarm_control_panel", "arm_night", {
        "entity_id": "alarm_control_panel.dt_alarm3",
    })
    state = await rest.get_state("alarm_control_panel.dt_alarm3")
    assert state["state"] == "armed_night"


async def test_alarm_disarm(rest):
    """alarm_control_panel.disarm sets disarmed."""
    await rest.set_state("alarm_control_panel.dt_alarm4", "armed_home")
    await rest.call_service("alarm_control_panel", "disarm", {
        "entity_id": "alarm_control_panel.dt_alarm4",
    })
    state = await rest.get_state("alarm_control_panel.dt_alarm4")
    assert state["state"] == "disarmed"


async def test_alarm_trigger(rest):
    """alarm_control_panel.trigger sets triggered."""
    await rest.set_state("alarm_control_panel.dt_alarm5", "armed_away")
    await rest.call_service("alarm_control_panel", "trigger", {
        "entity_id": "alarm_control_panel.dt_alarm5",
    })
    state = await rest.get_state("alarm_control_panel.dt_alarm5")
    assert state["state"] == "triggered"
