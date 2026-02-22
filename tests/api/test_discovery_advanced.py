"""
CTS -- Advanced MQTT Discovery Tests

Tests discovery edge cases: duplicate payloads, availability
topics, command topic publishing, JSON attribute payloads,
multi-entity devices, and discovery-based service dispatch.
"""

import asyncio
import json
import time

import httpx
import paho.mqtt.client as mqtt
import pytest

BASE = "http://localhost:8124"
MQTT_HOST = "localhost"
MQTT_PORT = 1884
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-dadv-{topic.replace('/', '-')[:18]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


# ── Duplicate Discovery ──────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_duplicate_payload():
    """Sending same discovery payload twice doesn't create duplicates."""
    payload = json.dumps({
        "name": "CTS Dup Sensor",
        "unique_id": "cts_adv_dup_1",
        "state_topic": "cts/sensor/dup1/state",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_dup_1/config", payload)
    await asyncio.sleep(0.5)
    mqtt_publish("homeassistant/sensor/cts_adv_dup_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_adv_dup_1")
    assert state is not None


# ── State Topic Update After Discovery ───────────────────

@pytest.mark.asyncio
async def test_discovery_state_tracks_topic():
    """After discovery, publishing to state_topic updates entity."""
    payload = json.dumps({
        "name": "CTS Tracking Sensor",
        "unique_id": "cts_adv_track_1",
        "state_topic": "cts/sensor/track1/state",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_track_1/config", payload)
    await asyncio.sleep(0.5)

    mqtt_publish("cts/sensor/track1/state", "99.5")
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_adv_track_1")
    assert state["state"] == "99.5"


@pytest.mark.asyncio
async def test_discovery_state_multiple_updates():
    """Multiple state updates to discovered entity work."""
    payload = json.dumps({
        "name": "CTS Multi Update",
        "unique_id": "cts_adv_multi_1",
        "state_topic": "cts/sensor/multi1/state",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_multi_1/config", payload)
    await asyncio.sleep(0.5)

    for val in ["10", "20", "30"]:
        mqtt_publish("cts/sensor/multi1/state", val)
        await asyncio.sleep(0.3)

    state = await get_state("sensor.cts_adv_multi_1")
    assert state["state"] == "30"


# ── JSON Attribute Payload ───────────────────────────────

@pytest.mark.asyncio
async def test_discovery_json_state_payload():
    """JSON payload on state topic stores attributes."""
    payload = json.dumps({
        "name": "CTS JSON Sensor",
        "unique_id": "cts_adv_json_1",
        "state_topic": "cts/sensor/json1/state",
        "value_template": "{{ value_json.value }}",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_json_1/config", payload)
    await asyncio.sleep(0.5)

    mqtt_publish("cts/sensor/json1/state", json.dumps({
        "value": 42,
        "unit": "lux",
    }))
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_adv_json_1")
    assert state is not None
    assert state["state"] == "42"


# ── Multi-Entity Device ─────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_multi_entity_device():
    """Multiple entities can share the same device identifier."""
    device_block = {
        "identifiers": ["cts_device_multi"],
        "name": "CTS Multi Device",
        "manufacturer": "CTS",
    }
    for component, uid, name in [
        ("sensor", "cts_adv_dev_temp", "Temperature"),
        ("sensor", "cts_adv_dev_hum", "Humidity"),
        ("binary_sensor", "cts_adv_dev_motion", "Motion"),
    ]:
        payload = json.dumps({
            "name": name,
            "unique_id": uid,
            "state_topic": f"cts/{component}/{uid}/state",
            "device": device_block,
        })
        mqtt_publish(f"homeassistant/{component}/{uid}/config", payload)

    await asyncio.sleep(0.8)

    for uid in ["cts_adv_dev_temp", "cts_adv_dev_hum"]:
        state = await get_state(f"sensor.{uid}")
        assert state is not None

    state = await get_state("binary_sensor.cts_adv_dev_motion")
    assert state is not None


# ── Discovery Component Types ───────────────────────────

@pytest.mark.asyncio
async def test_discovery_number():
    """Discovery for number component."""
    payload = json.dumps({
        "name": "CTS Volume",
        "unique_id": "cts_adv_number_1",
        "state_topic": "cts/number/vol1/state",
        "command_topic": "cts/number/vol1/set",
        "min": 0,
        "max": 100,
    })
    mqtt_publish("homeassistant/number/cts_adv_number_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("number.cts_adv_number_1")
    assert state is not None


@pytest.mark.asyncio
async def test_discovery_select():
    """Discovery for select component."""
    payload = json.dumps({
        "name": "CTS Mode Select",
        "unique_id": "cts_adv_select_1",
        "state_topic": "cts/select/mode1/state",
        "command_topic": "cts/select/mode1/set",
        "options": ["auto", "manual", "off"],
    })
    mqtt_publish("homeassistant/select/cts_adv_select_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("select.cts_adv_select_1")
    assert state is not None


@pytest.mark.asyncio
async def test_discovery_button():
    """Discovery for button component."""
    payload = json.dumps({
        "name": "CTS Reset Button",
        "unique_id": "cts_adv_button_1",
        "command_topic": "cts/button/reset1/set",
    })
    mqtt_publish("homeassistant/button/cts_adv_button_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("button.cts_adv_button_1")
    assert state is not None


@pytest.mark.asyncio
async def test_discovery_fan():
    """Discovery for fan component with initial state off."""
    payload = json.dumps({
        "name": "CTS Ceiling Fan",
        "unique_id": "cts_adv_fan_1",
        "state_topic": "cts/fan/ceiling1/state",
        "command_topic": "cts/fan/ceiling1/set",
        "speed_range_min": 1,
        "speed_range_max": 6,
    })
    mqtt_publish("homeassistant/fan/cts_adv_fan_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("fan.cts_adv_fan_1")
    assert state is not None
    assert state["state"] == "off"


@pytest.mark.asyncio
async def test_discovery_siren():
    """Discovery for siren component with initial state off."""
    payload = json.dumps({
        "name": "CTS Alarm Siren",
        "unique_id": "cts_adv_siren_1",
        "state_topic": "cts/siren/alarm1/state",
        "command_topic": "cts/siren/alarm1/set",
    })
    mqtt_publish("homeassistant/siren/cts_adv_siren_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("siren.cts_adv_siren_1")
    assert state is not None
    assert state["state"] == "off"


@pytest.mark.asyncio
async def test_discovery_valve():
    """Discovery for valve component with initial state closed."""
    payload = json.dumps({
        "name": "CTS Water Valve",
        "unique_id": "cts_adv_valve_1",
        "state_topic": "cts/valve/water1/state",
        "command_topic": "cts/valve/water1/set",
    })
    mqtt_publish("homeassistant/valve/cts_adv_valve_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("valve.cts_adv_valve_1")
    assert state is not None
    assert state["state"] == "closed"


# ── Discovery Attributes ────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_unit_of_measurement():
    """Discovery preserves unit_of_measurement."""
    payload = json.dumps({
        "name": "CTS Power",
        "unique_id": "cts_adv_unit_1",
        "state_topic": "cts/sensor/power1/state",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_unit_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_adv_unit_1")
    assert state["attributes"]["unit_of_measurement"] == "kWh"
    assert state["attributes"]["device_class"] == "energy"


@pytest.mark.asyncio
async def test_discovery_friendly_name_from_name():
    """Discovery sets friendly_name from name field."""
    payload = json.dumps({
        "name": "CTS Friendly Sensor",
        "unique_id": "cts_adv_friendly_1",
        "state_topic": "cts/sensor/friendly1/state",
    })
    mqtt_publish("homeassistant/sensor/cts_adv_friendly_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_adv_friendly_1")
    assert state["attributes"]["friendly_name"] == "CTS Friendly Sensor"


# ── Merged from test_discovery_removal.py ─────────────


@pytest.mark.marge_only
@pytest.mark.asyncio
async def test_discovery_create_then_remove():
    """Empty discovery payload removes the entity."""
    topic = "homeassistant/switch/disc_rm1/config"
    payload = json.dumps({
        "name": "Removable Switch",
        "unique_id": "disc_rm1",
        "state_topic": "home/switch/disc_rm1/state",
        "command_topic": "home/switch/disc_rm1/set",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("switch.disc_rm1")
    assert state is not None
    assert state["state"] == "off"

    # Remove via empty payload
    mqtt_publish(topic, "")
    await asyncio.sleep(0.5)

    state = await get_state("switch.disc_rm1")
    assert state is not None
    assert state["state"] == "unavailable"


@pytest.mark.asyncio
async def test_discovery_removal_idempotent():
    """Removing already-removed entity does not crash."""
    topic = "homeassistant/sensor/disc_rm2/config"
    payload = json.dumps({
        "name": "Temp Sensor",
        "unique_id": "disc_rm2",
        "state_topic": "sensors/disc_rm2",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    # Remove twice
    mqtt_publish(topic, "")
    await asyncio.sleep(0.3)
    mqtt_publish(topic, "")
    await asyncio.sleep(0.3)

    # Should not error -- entity is just unavailable
    state = await get_state("sensor.disc_rm2")
    assert state is not None


@pytest.mark.marge_only
@pytest.mark.asyncio
async def test_discovery_recreate_after_removal():
    """Entity can be recreated after removal."""
    topic = "homeassistant/light/disc_rm3/config"
    payload = json.dumps({
        "name": "Recreatable Light",
        "unique_id": "disc_rm3",
        "state_topic": "home/light/disc_rm3/state",
        "command_topic": "home/light/disc_rm3/set",
    })

    # Create
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)
    s1 = await get_state("light.disc_rm3")
    assert s1["state"] == "off"

    # Remove
    mqtt_publish(topic, "")
    await asyncio.sleep(0.5)
    s2 = await get_state("light.disc_rm3")
    assert s2["state"] == "unavailable"

    # Recreate
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)
    s3 = await get_state("light.disc_rm3")
    assert s3["state"] == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("avail_payload,expect_unavailable", [
    ("online", False),
    ("offline", True),
])
async def test_discovery_availability_status(avail_payload, expect_unavailable):
    """Publishing availability status updates entity availability."""
    uid = f"disc_avail_{avail_payload}"
    config_topic = f"homeassistant/sensor/{uid}/config"
    avail_topic = f"home/sensor/{uid}/availability"
    payload = json.dumps({
        "name": f"Avail Sensor {avail_payload}",
        "unique_id": uid,
        "state_topic": f"home/sensor/{uid}/state",
        "availability_topic": avail_topic,
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    # Set state first
    mqtt_publish(f"home/sensor/{uid}/state", "42")
    await asyncio.sleep(0.3)

    # Set availability
    mqtt_publish(avail_topic, avail_payload)
    await asyncio.sleep(0.3)

    state = await get_state(f"sensor.{uid}")
    assert state is not None
    if expect_unavailable:
        assert state["state"] == "unavailable"


@pytest.mark.asyncio
async def test_discovery_climate_multiple_topics():
    """Climate discovery with temperature and mode state topics."""
    config_topic = "homeassistant/climate/disc_clim1/config"
    payload = json.dumps({
        "name": "Test Climate",
        "unique_id": "disc_clim1",
        "temperature_command_topic": "climate/disc_clim1/temp/set",
        "temperature_state_topic": "climate/disc_clim1/temp/state",
        "mode_command_topic": "climate/disc_clim1/mode/set",
        "mode_state_topic": "climate/disc_clim1/mode/state",
        "modes": ["off", "heat", "cool", "auto"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("climate.disc_clim1")
    assert state is not None
    assert state["state"] == "off"
    assert "hvac_modes" in state["attributes"]


@pytest.mark.asyncio
async def test_discovery_cover_position_topic():
    """Cover discovery with position topic."""
    config_topic = "homeassistant/cover/disc_cov1/config"
    payload = json.dumps({
        "name": "Test Cover",
        "unique_id": "disc_cov1",
        "state_topic": "home/cover/disc_cov1/state",
        "command_topic": "home/cover/disc_cov1/set",
        "position_topic": "home/cover/disc_cov1/position",
        "set_position_topic": "home/cover/disc_cov1/position/set",
        "device_class": "garage",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("cover.disc_cov1")
    assert state is not None
    assert state["state"] == "closed"
    assert state["attributes"].get("device_class") == "garage"


@pytest.mark.asyncio
async def test_discovery_fan_speed_range():
    """Fan discovery with speed_range_max and preset_modes."""
    config_topic = "homeassistant/fan/disc_fan1/config"
    payload = json.dumps({
        "name": "Test Fan",
        "unique_id": "disc_fan1",
        "state_topic": "home/fan/disc_fan1/state",
        "command_topic": "home/fan/disc_fan1/set",
        "percentage_command_topic": "home/fan/disc_fan1/pct/set",
        "percentage_state_topic": "home/fan/disc_fan1/pct/state",
        "speed_range_max": 4,
        "preset_modes": ["auto", "breeze", "silent"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("fan.disc_fan1")
    assert state is not None
    assert state["state"] == "off"


@pytest.mark.asyncio
async def test_discovery_lock_payloads():
    """Lock discovery with custom payload_lock/unlock."""
    config_topic = "homeassistant/lock/disc_lock1/config"
    payload = json.dumps({
        "name": "Test Lock",
        "unique_id": "disc_lock1",
        "state_topic": "home/lock/disc_lock1/state",
        "command_topic": "home/lock/disc_lock1/set",
        "payload_lock": "LOCK",
        "payload_unlock": "UNLOCK",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("lock.disc_lock1")
    assert state is not None
    assert state["state"] == "locked"


@pytest.mark.asyncio
async def test_discovery_light_color_modes():
    """Light discovery with supported_color_modes and effect_list."""
    config_topic = "homeassistant/light/disc_lt1/config"
    payload = json.dumps({
        "name": "Color Light",
        "unique_id": "disc_lt1",
        "state_topic": "home/light/disc_lt1/state",
        "command_topic": "home/light/disc_lt1/set",
        "supported_color_modes": ["brightness", "color_temp", "rgb"],
        "effect_list": ["rainbow", "strobe", "calm"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("light.disc_lt1")
    assert state is not None
    assert "supported_color_modes" in state["attributes"]
    assert "effect_list" in state["attributes"]


@pytest.mark.asyncio
async def test_discovery_number_attributes():
    """Number discovery with min/max/step/mode."""
    config_topic = "homeassistant/number/disc_num1/config"
    payload = json.dumps({
        "name": "Test Number",
        "unique_id": "disc_num1",
        "state_topic": "home/number/disc_num1/state",
        "command_topic": "home/number/disc_num1/set",
        "min": 0,
        "max": 100,
        "step": 5,
        "mode": "slider",
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("number.disc_num1")
    assert state is not None
    assert state["attributes"].get("min") == 0
    assert state["attributes"].get("max") == 100
    assert state["attributes"].get("step") == 5
    assert state["attributes"].get("mode") == "slider"


@pytest.mark.asyncio
async def test_discovery_select_options():
    """Select discovery with options list."""
    config_topic = "homeassistant/select/disc_sel1/config"
    payload = json.dumps({
        "name": "Test Select",
        "unique_id": "disc_sel1",
        "state_topic": "home/select/disc_sel1/state",
        "command_topic": "home/select/disc_sel1/set",
        "options": ["option1", "option2", "option3"],
    })
    mqtt_publish(config_topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("select.disc_sel1")
    assert state is not None
    assert state["attributes"].get("options") == ["option1", "option2", "option3"]


@pytest.mark.asyncio
async def test_discovery_node_id_topic():
    """Discovery with 5-segment topic (node_id present)."""
    topic = "homeassistant/sensor/z2m_bridge/disc_node1/config"
    payload = json.dumps({
        "name": "Node Sensor",
        "unique_id": "disc_node1",
        "state_topic": "home/sensor/disc_node1/state",
    })
    mqtt_publish(topic, payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.disc_node1")
    assert state is not None
