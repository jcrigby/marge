"""
CTS -- MQTT Bridge Topic Routing Tests

Tests MQTT topic->entity_id mapping via the home/# bridge on Marge's
embedded broker (port 1884), and MQTT-driven state changes via REST.
"""

import asyncio
import time
import uuid
import pytest
import httpx
import paho.mqtt.client as mqtt

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
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


async def set_state(entity_id: str, state: str, attrs=None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code in (200, 201)


async def test_mqtt_sensor_state_update():
    """MQTT publish to home/sensor/x/state creates entity."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"home/sensor/topic_{tag}/state", "42.5")
    await asyncio.sleep(0.3)

    s = await get_state(f"sensor.topic_{tag}")
    assert s is not None
    assert s["state"] == "42.5"


async def test_mqtt_binary_sensor_state():
    """MQTT binary_sensor topic creates entity with correct state."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"home/binary_sensor/bs_{tag}/state", "ON")
    await asyncio.sleep(0.3)

    s = await get_state(f"binary_sensor.bs_{tag}")
    assert s is not None
    assert s["state"] == "ON"


async def test_mqtt_switch_on_off():
    """MQTT switch state transitions ON/OFF."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sw_{tag}"

    mqtt_publish(f"home/switch/sw_{tag}/state", "ON")
    await asyncio.sleep(0.3)
    s = await get_state(eid)
    assert s["state"] == "ON"

    mqtt_publish(f"home/switch/sw_{tag}/state", "OFF")
    await asyncio.sleep(0.3)
    s = await get_state(eid)
    assert s["state"] == "OFF"


async def test_mqtt_preserves_attributes():
    """MQTT state update preserves existing entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqattr_{tag}"

    await set_state(eid, "initial", {"unit": "celsius", "device": "probe"})

    mqtt_publish(f"home/sensor/mqattr_{tag}/state", "25.0")
    await asyncio.sleep(0.3)

    s = await get_state(eid)
    assert s["state"] == "25.0"
    assert s["attributes"]["unit"] == "celsius"
    assert s["attributes"]["device"] == "probe"


async def test_mqtt_non_matching_topic_ignored():
    """Topics not matching home/{d}/{id}/state don't create entities."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"random/topic/{tag}", "value")
    await asyncio.sleep(0.3)

    s = await get_state(f"random.topic_{tag}")
    assert s is None


async def test_mqtt_light_domain():
    """MQTT light topic creates light entity."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"home/light/mqlight_{tag}/state", "on")
    await asyncio.sleep(0.3)

    s = await get_state(f"light.mqlight_{tag}")
    assert s is not None
    assert s["state"] == "on"


async def test_mqtt_multiple_domains():
    """MQTT creates entities across different domains."""
    tag = uuid.uuid4().hex[:8]

    for domain in ["sensor", "binary_sensor", "switch", "light", "lock"]:
        mqtt_publish(f"home/{domain}/multi_{tag}/state", "active")
        await asyncio.sleep(0.2)

    for domain in ["sensor", "binary_sensor", "switch", "light", "lock"]:
        s = await get_state(f"{domain}.multi_{tag}")
        assert s is not None, f"{domain}.multi_{tag} should exist"
        assert s["state"] == "active"
