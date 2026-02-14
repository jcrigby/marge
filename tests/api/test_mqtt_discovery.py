"""
CTS -- MQTT Discovery Protocol Tests

Tests HA MQTT Discovery by publishing discovery payloads to
Marge's embedded broker and verifying entities are auto-created
with correct attributes, state topics, and command topics.
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
                    client_id=f"cts-disc-{topic.replace('/', '-')[:20]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


# ── Sensor Discovery ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_sensor():
    """Discovery payload for sensor creates entity."""
    payload = json.dumps({
        "name": "CTS Temperature",
        "unique_id": "cts_disc_temp_1",
        "state_topic": "cts/sensor/temp1/state",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
    })
    mqtt_publish("homeassistant/sensor/cts_disc_temp_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_temp_1")
    assert state is not None
    assert state["attributes"].get("friendly_name") == "CTS Temperature"
    assert state["attributes"].get("unit_of_measurement") == "°C"
    assert state["attributes"].get("device_class") == "temperature"


@pytest.mark.asyncio
async def test_discovery_sensor_state_update():
    """State topic update changes discovered entity state."""
    # Ensure entity exists
    payload = json.dumps({
        "name": "CTS State Update",
        "unique_id": "cts_disc_state_upd",
        "state_topic": "cts/sensor/state_upd/state",
    })
    mqtt_publish("homeassistant/sensor/cts_disc_state_upd/config", payload)
    await asyncio.sleep(0.5)

    # Publish state
    mqtt_publish("cts/sensor/state_upd/state", "42.5")
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_state_upd")
    assert state is not None
    assert state["state"] == "42.5"


# ── Binary Sensor Discovery ──────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_binary_sensor():
    """Discovery payload for binary_sensor creates entity."""
    payload = json.dumps({
        "name": "CTS Motion",
        "unique_id": "cts_disc_motion_1",
        "state_topic": "cts/binary_sensor/motion1/state",
        "device_class": "motion",
        "payload_on": "ON",
        "payload_off": "OFF",
    })
    mqtt_publish("homeassistant/binary_sensor/cts_disc_motion_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("binary_sensor.cts_disc_motion_1")
    assert state is not None
    assert state["attributes"].get("device_class") == "motion"


# ── Light Discovery ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_light():
    """Discovery payload for light creates entity with command_topic."""
    payload = json.dumps({
        "name": "CTS Light",
        "unique_id": "cts_disc_light_1",
        "state_topic": "cts/light/light1/state",
        "command_topic": "cts/light/light1/set",
    })
    mqtt_publish("homeassistant/light/cts_disc_light_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("light.cts_disc_light_1")
    assert state is not None
    assert state["state"] == "off"  # Initial state for lights


# ── Switch Discovery ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_switch():
    """Discovery payload for switch creates entity."""
    payload = json.dumps({
        "name": "CTS Switch",
        "unique_id": "cts_disc_switch_1",
        "state_topic": "cts/switch/switch1/state",
        "command_topic": "cts/switch/switch1/set",
    })
    mqtt_publish("homeassistant/switch/cts_disc_switch_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("switch.cts_disc_switch_1")
    assert state is not None
    assert state["state"] == "off"


# ── Climate Discovery ────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_climate():
    """Discovery payload for climate creates entity."""
    payload = json.dumps({
        "name": "CTS Thermostat",
        "unique_id": "cts_disc_climate_1",
        "temperature_command_topic": "cts/climate/therm1/temp/set",
        "temperature_state_topic": "cts/climate/therm1/temp/state",
        "mode_command_topic": "cts/climate/therm1/mode/set",
        "mode_state_topic": "cts/climate/therm1/mode/state",
        "modes": ["off", "heat", "cool", "auto"],
    })
    mqtt_publish("homeassistant/climate/cts_disc_climate_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("climate.cts_disc_climate_1")
    assert state is not None
    assert state["state"] == "off"  # Initial state for climate


# ── Cover Discovery ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_cover():
    """Discovery payload for cover creates entity."""
    payload = json.dumps({
        "name": "CTS Garage",
        "unique_id": "cts_disc_cover_1",
        "state_topic": "cts/cover/garage1/state",
        "command_topic": "cts/cover/garage1/set",
    })
    mqtt_publish("homeassistant/cover/cts_disc_cover_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("cover.cts_disc_cover_1")
    assert state is not None
    assert state["state"] == "closed"  # Initial state for covers


# ── Lock Discovery ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_lock():
    """Discovery payload for lock creates entity."""
    payload = json.dumps({
        "name": "CTS Door Lock",
        "unique_id": "cts_disc_lock_1",
        "state_topic": "cts/lock/door1/state",
        "command_topic": "cts/lock/door1/set",
        "payload_lock": "LOCK",
        "payload_unlock": "UNLOCK",
    })
    mqtt_publish("homeassistant/lock/cts_disc_lock_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("lock.cts_disc_lock_1")
    assert state is not None
    assert state["state"] == "locked"  # Initial state for locks


# ── Device Info ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_with_device_info():
    """Discovery with device block creates entity with device attributes."""
    payload = json.dumps({
        "name": "CTS Device Sensor",
        "unique_id": "cts_disc_dev_sensor_1",
        "state_topic": "cts/sensor/dev_sensor1/state",
        "device": {
            "identifiers": ["cts_device_1"],
            "name": "CTS Test Device",
            "manufacturer": "CTS Corp",
            "model": "Tester-3000",
        },
    })
    mqtt_publish("homeassistant/sensor/cts_disc_dev_sensor_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_dev_sensor_1")
    assert state is not None
    assert state["attributes"].get("friendly_name") == "CTS Device Sensor"


# ── Topic Depth ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_5_part_topic():
    """Discovery with 5-part topic (node_id/object_id) works."""
    payload = json.dumps({
        "name": "CTS Node Sensor",
        "unique_id": "cts_disc_node_1",
        "object_id": "cts_disc_node_1",
        "state_topic": "cts/sensor/node_sensor/state",
    })
    mqtt_publish("homeassistant/sensor/node1/cts_disc_node_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_node_1")
    assert state is not None


# ── Entity Removal ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_empty_payload_removes_entity():
    """Empty discovery payload removes previously discovered entity."""
    # Create entity
    payload = json.dumps({
        "name": "CTS Remove Me",
        "unique_id": "cts_disc_remove_1",
        "state_topic": "cts/sensor/remove1/state",
    })
    mqtt_publish("homeassistant/sensor/cts_disc_remove_1/config", payload)
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_remove_1")
    assert state is not None

    # Remove with empty payload
    mqtt_publish("homeassistant/sensor/cts_disc_remove_1/config", "")
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_remove_1")
    # Entity should be removed (404) or state should be unavailable
    # Depending on implementation
    assert state is None or state["state"] == "unavailable"


# ── Value Template ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_discovery_value_template():
    """Value template extracts state from JSON payload."""
    payload = json.dumps({
        "name": "CTS Template Sensor",
        "unique_id": "cts_disc_tmpl_1",
        "state_topic": "cts/sensor/tmpl1/state",
        "value_template": "{{ value_json.temperature }}",
    })
    mqtt_publish("homeassistant/sensor/cts_disc_tmpl_1/config", payload)
    await asyncio.sleep(0.5)

    # Publish JSON state
    mqtt_publish("cts/sensor/tmpl1/state", json.dumps({"temperature": 23.5, "humidity": 45}))
    await asyncio.sleep(0.5)

    state = await get_state("sensor.cts_disc_tmpl_1")
    assert state is not None
    assert state["state"] == "23.5"
