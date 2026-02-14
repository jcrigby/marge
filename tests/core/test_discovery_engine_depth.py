"""
CTS -- MQTT Discovery Engine Depth Tests

Tests discovery config payload processing: initial state per component,
device_class/unit_of_measurement attributes, empty payload removal,
and four-level topic parsing (homeassistant/+/+/+/config).
"""

import asyncio
import json
import time
import uuid

import httpx
import paho.mqtt.client as mqtt
import pytest

BASE = "http://localhost:8124"
MQTT_HOST = "localhost"
MQTT_PORT = 1884
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}

pytestmark = pytest.mark.asyncio


def mqtt_publish(topic: str, payload: str):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-disc-{uuid.uuid4().hex[:8]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


async def test_discovery_sensor_initial_unknown():
    """Discovered sensor starts in 'unknown' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Temp {tag}",
        "unique_id": f"sensor_{tag}",
        "state_topic": f"test/{tag}/state",
        "device_class": "temperature",
        "unit_of_measurement": "°C",
    })
    mqtt_publish(f"homeassistant/sensor/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"sensor.{tag}")
    assert state is not None
    assert state["state"] == "unknown"
    assert state["attributes"].get("device_class") == "temperature"
    assert state["attributes"].get("unit_of_measurement") == "°C"


async def test_discovery_binary_sensor_initial_unknown():
    """Discovered binary_sensor starts in 'unknown' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Motion {tag}",
        "unique_id": f"bs_{tag}",
        "state_topic": f"test/{tag}/bs/state",
        "device_class": "motion",
    })
    mqtt_publish(f"homeassistant/binary_sensor/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"binary_sensor.{tag}")
    assert state is not None
    assert state["state"] == "unknown"


async def test_discovery_switch_initial_off():
    """Discovered switch starts in 'off' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Relay {tag}",
        "unique_id": f"sw_{tag}",
        "state_topic": f"test/{tag}/switch/state",
        "command_topic": f"test/{tag}/switch/set",
    })
    mqtt_publish(f"homeassistant/switch/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"switch.{tag}")
    assert state is not None
    assert state["state"] == "off"


async def test_discovery_light_initial_off():
    """Discovered light starts in 'off' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Bulb {tag}",
        "unique_id": f"lt_{tag}",
        "state_topic": f"test/{tag}/light/state",
        "command_topic": f"test/{tag}/light/set",
    })
    mqtt_publish(f"homeassistant/light/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"light.{tag}")
    assert state is not None
    assert state["state"] == "off"


async def test_discovery_lock_initial_locked():
    """Discovered lock starts in 'locked' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Lock {tag}",
        "unique_id": f"lk_{tag}",
        "state_topic": f"test/{tag}/lock/state",
        "command_topic": f"test/{tag}/lock/set",
    })
    mqtt_publish(f"homeassistant/lock/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"lock.{tag}")
    assert state is not None
    assert state["state"] == "locked"


async def test_discovery_cover_initial_closed():
    """Discovered cover starts in 'closed' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Shade {tag}",
        "unique_id": f"cv_{tag}",
        "state_topic": f"test/{tag}/cover/state",
        "command_topic": f"test/{tag}/cover/set",
    })
    mqtt_publish(f"homeassistant/cover/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"cover.{tag}")
    assert state is not None
    assert state["state"] == "closed"


async def test_discovery_climate_initial_off():
    """Discovered climate starts in 'off' state."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"HVAC {tag}",
        "unique_id": f"cl_{tag}",
        "state_topic": f"test/{tag}/climate/state",
        "modes": ["off", "heat", "cool"],
    })
    mqtt_publish(f"homeassistant/climate/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"climate.{tag}")
    assert state is not None
    assert state["state"] == "off"


async def test_discovery_with_device_info():
    """Discovery with device payload stores friendly_name."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Device Sensor {tag}",
        "unique_id": f"devsens_{tag}",
        "state_topic": f"test/{tag}/devsens/state",
        "device": {
            "identifiers": [f"dev_{tag}"],
            "name": f"Test Device {tag}",
            "manufacturer": "Acme",
            "model": "Widget 3000",
        },
    })
    mqtt_publish(f"homeassistant/sensor/{tag}_dev/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"sensor.{tag}_dev")
    assert state is not None
    assert state["attributes"].get("friendly_name") == f"Device Sensor {tag}"


async def test_discovery_empty_payload_removes():
    """Empty payload on discovery topic marks entity unavailable."""
    tag = uuid.uuid4().hex[:8]
    # Create first
    config = json.dumps({
        "name": f"Removable {tag}",
        "unique_id": f"rm_{tag}",
        "state_topic": f"test/{tag}/rm/state",
    })
    mqtt_publish(f"homeassistant/sensor/{tag}_rm/config", config)
    await asyncio.sleep(0.5)
    state = await get_state(f"sensor.{tag}_rm")
    assert state is not None
    assert state["state"] == "unknown"  # sensor initial state

    # Remove with empty payload — entity becomes unavailable
    mqtt_publish(f"homeassistant/sensor/{tag}_rm/config", "")
    await asyncio.sleep(0.5)
    state = await get_state(f"sensor.{tag}_rm")
    assert state is not None
    assert state["state"] == "unavailable"


async def test_discovery_four_level_topic():
    """Four-level topic (homeassistant/+/node/+/config) works."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Node Sensor {tag}",
        "unique_id": f"ns_{tag}",
        "state_topic": f"test/{tag}/node/state",
    })
    mqtt_publish(f"homeassistant/sensor/node_{tag}/{tag}/config", config)
    await asyncio.sleep(0.5)

    state = await get_state(f"sensor.{tag}")
    assert state is not None


async def test_discovery_object_id_override():
    """object_id in payload overrides topic-derived ID."""
    tag = uuid.uuid4().hex[:8]
    config = json.dumps({
        "name": f"Override {tag}",
        "unique_id": f"ovr_{tag}",
        "object_id": f"custom_id_{tag}",
        "state_topic": f"test/{tag}/ovr/state",
    })
    mqtt_publish(f"homeassistant/sensor/topic_id_{tag}/config", config)
    await asyncio.sleep(0.5)

    # Entity should use object_id, not topic-derived ID
    state = await get_state(f"sensor.custom_id_{tag}")
    assert state is not None
