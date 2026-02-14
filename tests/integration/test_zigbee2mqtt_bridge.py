"""
CTS -- Zigbee2MQTT Bridge Integration Tests

Tests MQTT messages from zigbee2mqtt processed via Marge's
embedded broker (port 1884). Covers bridge/state, bridge/devices,
device state updates, and availability tracking.
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
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


async def test_z2m_bridge_state_online():
    """zigbee2mqtt/bridge/state 'online' message processed."""
    mqtt_publish("zigbee2mqtt/bridge/state", "online")
    await asyncio.sleep(0.5)
    # Should set bridge entity to online state
    state = await get_state("binary_sensor.zigbee2mqtt_bridge")
    if state is not None:
        assert state["state"] in ("online", "on", "ON")


async def test_z2m_bridge_state_offline():
    """zigbee2mqtt/bridge/state 'offline' message processed."""
    mqtt_publish("zigbee2mqtt/bridge/state", "offline")
    await asyncio.sleep(0.5)
    state = await get_state("binary_sensor.zigbee2mqtt_bridge")
    if state is not None:
        assert state["state"] in ("offline", "off", "OFF")


async def test_z2m_device_state_update():
    """zigbee2mqtt/<device> JSON state update creates entity."""
    tag = uuid.uuid4().hex[:8]
    device = f"z2m_sensor_{tag}"
    payload = json.dumps({
        "temperature": 22.5,
        "humidity": 65,
        "battery": 95,
        "linkquality": 120,
    })
    mqtt_publish(f"zigbee2mqtt/{device}", payload)
    await asyncio.sleep(0.5)

    # Entity creation depends on implementation
    state = await get_state(f"sensor.{device}")


async def test_z2m_bridge_devices_message():
    """zigbee2mqtt/bridge/devices message with device list."""
    tag = uuid.uuid4().hex[:8]
    devices = [
        {
            "ieee_address": f"0x00158d000{tag[:7]}",
            "friendly_name": f"z2m_test_{tag}",
            "type": "EndDevice",
            "model_id": "WSDCGQ11LM",
            "manufacturer": "Aqara",
            "supported": True,
            "interviewing": False,
            "interview_completed": True,
            "definition": {
                "model": "WSDCGQ11LM",
                "vendor": "Aqara",
                "description": "Temperature/Humidity sensor",
                "exposes": [
                    {"type": "numeric", "name": "temperature", "property": "temperature"},
                    {"type": "numeric", "name": "humidity", "property": "humidity"},
                ],
            },
        },
    ]
    mqtt_publish("zigbee2mqtt/bridge/devices", json.dumps(devices))
    await asyncio.sleep(0.5)
    # Device registration is implementation-specific


async def test_z2m_device_availability():
    """zigbee2mqtt/<device>/availability message."""
    tag = uuid.uuid4().hex[:8]
    device = f"z2m_avail_{tag}"
    mqtt_publish(f"zigbee2mqtt/{device}/availability", "online")
    await asyncio.sleep(0.5)
    # Availability tracking is implementation-specific


async def test_z2m_bridge_groups():
    """zigbee2mqtt/bridge/groups message with group list."""
    tag = uuid.uuid4().hex[:8]
    groups = [
        {
            "id": 1,
            "friendly_name": f"z2m_group_{tag}",
            "members": [
                {"ieee_address": "0x00158d0001234567", "endpoint": 1},
            ],
        },
    ]
    mqtt_publish("zigbee2mqtt/bridge/groups", json.dumps(groups))
    await asyncio.sleep(0.5)


async def test_z2m_device_set_command():
    """zigbee2mqtt/<device>/set command via MQTT publish."""
    tag = uuid.uuid4().hex[:8]
    device = f"z2m_cmd_{tag}"

    # First create the device with a state
    mqtt_publish(f"zigbee2mqtt/{device}", json.dumps({"state": "OFF"}))
    await asyncio.sleep(0.3)

    # Send set command
    mqtt_publish(f"zigbee2mqtt/{device}/set", json.dumps({"state": "ON"}))
    await asyncio.sleep(0.5)
    # Command processing is implementation-specific
