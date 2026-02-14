"""
CTS -- MQTT State Bridge Depth Tests

Tests the MQTT → state machine bridge: publishing to home/{domain}/{id}/state
topics creates/updates entities in the state machine. Also tests topic
format validation and attribute preservation through MQTT.
"""

import asyncio
import time
import uuid

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


async def set_state(entity_id: str, state: str, attrs=None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-msb-{topic.replace('/', '-')[:18]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


# ── Basic MQTT → State ─────────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_publish_creates_entity():
    """Publishing to home/{domain}/{id}/state creates entity."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/sensor/mqtt_{tag}/state"
    mqtt_publish(topic, "42")
    await asyncio.sleep(0.5)
    state = await get_state(f"sensor.mqtt_{tag}")
    assert state is not None
    assert state["state"] == "42"


@pytest.mark.asyncio
async def test_mqtt_publish_updates_entity():
    """Publishing again updates entity state."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/sensor/mqtt_upd_{tag}/state"
    mqtt_publish(topic, "10")
    await asyncio.sleep(0.3)
    mqtt_publish(topic, "20")
    await asyncio.sleep(0.3)
    state = await get_state(f"sensor.mqtt_upd_{tag}")
    assert state is not None
    assert state["state"] == "20"


@pytest.mark.asyncio
async def test_mqtt_binary_sensor():
    """Publishing to binary_sensor topic creates binary_sensor entity."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/binary_sensor/mqtt_bs_{tag}/state"
    mqtt_publish(topic, "ON")
    await asyncio.sleep(0.3)
    state = await get_state(f"binary_sensor.mqtt_bs_{tag}")
    assert state is not None
    assert state["state"] == "ON"


@pytest.mark.asyncio
async def test_mqtt_light_state():
    """Publishing to light topic sets light state."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/light/mqtt_lt_{tag}/state"
    mqtt_publish(topic, "on")
    await asyncio.sleep(0.3)
    state = await get_state(f"light.mqtt_lt_{tag}")
    assert state is not None
    assert state["state"] == "on"


@pytest.mark.asyncio
async def test_mqtt_switch_state():
    """Publishing to switch topic sets switch state."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/switch/mqtt_sw_{tag}/state"
    mqtt_publish(topic, "OFF")
    await asyncio.sleep(0.3)
    state = await get_state(f"switch.mqtt_sw_{tag}")
    assert state is not None
    assert state["state"] == "OFF"


# ── Attribute Preservation ──────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_preserves_existing_attributes():
    """MQTT state update preserves existing entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqtt_attr_{tag}"
    await set_state(eid, "0", {"unit": "W", "friendly_name": "MQTT Sensor"})
    topic = f"home/sensor/mqtt_attr_{tag}/state"
    mqtt_publish(topic, "100")
    await asyncio.sleep(0.3)
    state = await get_state(eid)
    assert state is not None
    assert state["state"] == "100"
    assert state["attributes"]["unit"] == "W"
    assert state["attributes"]["friendly_name"] == "MQTT Sensor"


# ── Multiple Entities ──────────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_multiple_entities():
    """Multiple MQTT publishes create independent entities."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        topic = f"home/sensor/mqtt_m{i}_{tag}/state"
        mqtt_publish(topic, str(i * 10))
    await asyncio.sleep(0.5)
    for i in range(3):
        state = await get_state(f"sensor.mqtt_m{i}_{tag}")
        assert state is not None
        assert state["state"] == str(i * 10)


# ── MQTT Domain Variety ───────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_cover_state():
    """Publishing to cover topic sets cover state."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/cover/mqtt_cv_{tag}/state"
    mqtt_publish(topic, "open")
    await asyncio.sleep(0.3)
    state = await get_state(f"cover.mqtt_cv_{tag}")
    assert state is not None
    assert state["state"] == "open"


@pytest.mark.asyncio
async def test_mqtt_fan_state():
    """Publishing to fan topic sets fan state."""
    tag = uuid.uuid4().hex[:8]
    topic = f"home/fan/mqtt_fn_{tag}/state"
    mqtt_publish(topic, "on")
    await asyncio.sleep(0.3)
    state = await get_state(f"fan.mqtt_fn_{tag}")
    assert state is not None
    assert state["state"] == "on"
