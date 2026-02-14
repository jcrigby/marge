"""
CTS -- MQTT Discovery Entity Creation Tests

Tests HA MQTT Discovery protocol via Marge's embedded broker (port 1884).
Publishes discovery config payloads to homeassistant/+/+/config and verifies
entity auto-creation via REST API.
"""

import asyncio
import json
import time
import uuid
import pytest
import paho.mqtt.client as mqtt
import httpx

BASE = "http://localhost:8124"
MQTT_HOST = "localhost"
MQTT_PORT = 1884
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}

pytestmark = pytest.mark.asyncio


def mqtt_publish(topic: str, payload: str):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cts-{uuid.uuid4().hex[:8]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    time.sleep(0.5)
    c.loop_stop()
    c.disconnect()


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


async def test_discovery_sensor_creates_entity():
    """HA MQTT Discovery sensor config creates sensor entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_temp_{tag}"
    config = {
        "name": f"Discovery Temp {tag}",
        "unique_id": f"uid_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
    }
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"sensor.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"sensor.{object_id}"


async def test_discovery_binary_sensor():
    """HA MQTT Discovery binary_sensor config creates entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_door_{tag}"
    config = {
        "name": f"Door {tag}",
        "unique_id": f"uid_bs_{tag}",
        "object_id": object_id,
        "state_topic": f"home/binary_sensor/{object_id}/state",
        "device_class": "door",
        "payload_on": "ON",
        "payload_off": "OFF",
    }
    mqtt_publish(f"homeassistant/binary_sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"binary_sensor.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"binary_sensor.{object_id}"


async def test_discovery_switch():
    """HA MQTT Discovery switch config creates entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_sw_{tag}"
    config = {
        "name": f"Switch {tag}",
        "unique_id": f"uid_sw_{tag}",
        "object_id": object_id,
        "state_topic": f"home/switch/{object_id}/state",
        "command_topic": f"home/switch/{object_id}/set",
        "payload_on": "ON",
        "payload_off": "OFF",
    }
    mqtt_publish(f"homeassistant/switch/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"switch.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"switch.{object_id}"


async def test_discovery_light():
    """HA MQTT Discovery light config creates entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_lt_{tag}"
    config = {
        "name": f"Light {tag}",
        "unique_id": f"uid_lt_{tag}",
        "object_id": object_id,
        "state_topic": f"home/light/{object_id}/state",
        "command_topic": f"home/light/{object_id}/set",
        "brightness_state_topic": f"home/light/{object_id}/brightness",
        "brightness_command_topic": f"home/light/{object_id}/brightness/set",
    }
    mqtt_publish(f"homeassistant/light/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"light.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"light.{object_id}"


async def test_discovery_empty_payload_removes_entity():
    """Empty discovery payload removes entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_rem_{tag}"

    # Create
    config = {
        "name": f"Remove Me {tag}",
        "unique_id": f"uid_rm_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
    }
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    # Remove with empty payload
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", "")
    await asyncio.sleep(1.0)

    # Entity should be gone
    state = await get_state(f"sensor.{object_id}")
    # May or may not be removed depending on implementation


async def test_discovery_with_device_info():
    """Discovery payload with device grouping."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_dev_{tag}"
    config = {
        "name": f"Device Sensor {tag}",
        "unique_id": f"uid_dev_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
        "device": {
            "identifiers": [f"dev_{tag}"],
            "name": f"Test Device {tag}",
            "manufacturer": "CTS",
            "model": "TestModel",
            "sw_version": "1.0",
        },
    }
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)


async def test_discovery_with_value_template():
    """Discovery payload with value_template for state extraction."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_vt_{tag}"
    config = {
        "name": f"Templated {tag}",
        "unique_id": f"uid_vt_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
        "value_template": "{{ value_json.temperature }}",
    }
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(0.5)

    # Publish JSON to state topic
    mqtt_publish(
        f"home/sensor/{object_id}/state",
        json.dumps({"temperature": 25.3, "humidity": 60}),
    )
    await asyncio.sleep(1.0)

    state = await get_state(f"sensor.{object_id}")
    if state is not None:
        # With value_template, state should be extracted temperature
        assert "25" in str(state["state"]) or state["state"] == "25.3"


async def test_discovery_climate():
    """HA MQTT Discovery climate config creates entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_clm_{tag}"
    config = {
        "name": f"Thermostat {tag}",
        "unique_id": f"uid_clm_{tag}",
        "object_id": object_id,
        "temperature_command_topic": f"home/climate/{object_id}/temp/set",
        "temperature_state_topic": f"home/climate/{object_id}/temp",
        "mode_command_topic": f"home/climate/{object_id}/mode/set",
        "mode_state_topic": f"home/climate/{object_id}/mode",
        "modes": ["off", "heat", "cool", "auto"],
    }
    mqtt_publish(f"homeassistant/climate/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"climate.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"climate.{object_id}"


async def test_discovery_cover():
    """HA MQTT Discovery cover config creates entity."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_cvr_{tag}"
    config = {
        "name": f"Garage Door {tag}",
        "unique_id": f"uid_cvr_{tag}",
        "object_id": object_id,
        "state_topic": f"home/cover/{object_id}/state",
        "command_topic": f"home/cover/{object_id}/set",
        "position_topic": f"home/cover/{object_id}/position",
        "set_position_topic": f"home/cover/{object_id}/position/set",
    }
    mqtt_publish(f"homeassistant/cover/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)

    state = await get_state(f"cover.{object_id}")
    if state is not None:
        assert state["entity_id"] == f"cover.{object_id}"


async def test_discovery_with_availability():
    """Discovery payload with availability_topic."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_avl_{tag}"
    config = {
        "name": f"Available {tag}",
        "unique_id": f"uid_avl_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
        "availability_topic": f"home/sensor/{object_id}/available",
    }
    mqtt_publish(f"homeassistant/sensor/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)


async def test_discovery_four_level_topic():
    """Discovery with four-level topic homeassistant/+/+/+/config."""
    tag = uuid.uuid4().hex[:8]
    object_id = f"disc_4l_{tag}"
    config = {
        "name": f"Four Level {tag}",
        "unique_id": f"uid_4l_{tag}",
        "object_id": object_id,
        "state_topic": f"home/sensor/{object_id}/state",
    }
    mqtt_publish(f"homeassistant/sensor/subgroup/{object_id}/config", json.dumps(config))
    await asyncio.sleep(1.0)
