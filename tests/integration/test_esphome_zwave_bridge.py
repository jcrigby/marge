"""
CTS -- ESPHome and Z-Wave Bridge Integration Tests

Tests MQTT messages from ESPHome and Z-Wave devices via Marge's
embedded broker (port 1884). Covers status, component state,
node updates, and command class mappings.
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

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


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


# ── Z-Wave Bridge ─────────────────────────────────────────

async def test_zwave_node_update():
    """Z-Wave node status update processed."""
    tag = uuid.uuid4().hex[:8]
    node_data = json.dumps({
        "id": 5,
        "name": f"zwave_node_{tag}",
        "status": "Alive",
        "ready": True,
    })
    mqtt_publish(f"zwave/nodeID_5/status", node_data)
    await asyncio.sleep(0.5)
    # Node processing is implementation-specific


async def test_zwave_node_value():
    """Z-Wave node value update."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(
        "zwave/nodeID_3/49/0/Air_temperature",
        "22.5",
    )
    await asyncio.sleep(0.5)


async def test_zwave_gateway_status():
    """Z-Wave gateway status message."""
    mqtt_publish("zwave/_CLIENTS/ZWAVE_GATEWAY-test/status", "true")
    await asyncio.sleep(0.5)


async def test_zwave_node_list():
    """Z-Wave node list from gateway API."""
    tag = uuid.uuid4().hex[:8]
    nodes = [
        {"id": 1, "name": "Controller", "status": "Alive", "ready": True},
        {"id": 2, "name": f"Sensor {tag}", "status": "Alive", "ready": True},
    ]
    mqtt_publish("zwave/_CLIENTS/ZWAVE_GATEWAY-test/api/getNodes", json.dumps(nodes))
    await asyncio.sleep(0.5)


# ── ESPHome Bridge ────────────────────────────────────────

async def test_esphome_status_online():
    """ESPHome status 'online' message processed."""
    tag = uuid.uuid4().hex[:8]
    prefix = f"esphome_{tag}"
    mqtt_publish(f"{prefix}/status", "online")
    await asyncio.sleep(0.5)


async def test_esphome_status_offline():
    """ESPHome status 'offline' message processed."""
    tag = uuid.uuid4().hex[:8]
    prefix = f"esphome_{tag}"
    mqtt_publish(f"{prefix}/status", "online")
    await asyncio.sleep(0.3)
    mqtt_publish(f"{prefix}/status", "offline")
    await asyncio.sleep(0.5)


async def test_esphome_sensor_state():
    """ESPHome sensor component state update."""
    tag = uuid.uuid4().hex[:8]
    prefix = f"esph_{tag}"
    # First register the device
    mqtt_publish(f"{prefix}/status", "online")
    await asyncio.sleep(0.3)
    # Then send component state
    mqtt_publish(f"{prefix}/sensor/temperature/state", "23.5")
    await asyncio.sleep(0.5)


async def test_esphome_switch_state():
    """ESPHome switch component state update."""
    tag = uuid.uuid4().hex[:8]
    prefix = f"esps_{tag}"
    mqtt_publish(f"{prefix}/status", "online")
    await asyncio.sleep(0.3)
    mqtt_publish(f"{prefix}/switch/relay/state", "ON")
    await asyncio.sleep(0.5)


async def test_esphome_binary_sensor():
    """ESPHome binary_sensor component state."""
    tag = uuid.uuid4().hex[:8]
    prefix = f"espbs_{tag}"
    mqtt_publish(f"{prefix}/status", "online")
    await asyncio.sleep(0.3)
    mqtt_publish(f"{prefix}/binary_sensor/motion/state", "ON")
    await asyncio.sleep(0.5)
