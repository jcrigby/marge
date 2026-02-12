"""CTS — MQTT bridge tests.

Tests that MQTT publishes to Marge's embedded broker
are bridged into the state machine and trigger automations.
"""
import asyncio
import pytest
import httpx
import paho.mqtt.client as mqtt

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


async def set_state(entity_id: str, state: str, attrs: dict | None = None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200


def mqtt_publish(topic: str, payload: str):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cts-{topic.replace('/', '-')}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    import time; time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


@pytest.mark.asyncio
async def test_mqtt_sensor_bridges_to_state():
    """MQTT publish on sensor topic creates/updates entity in state machine."""
    mqtt_publish("home/sensor/test_mqtt_bridge/state", "42.5")
    await asyncio.sleep(0.3)

    s = await get_state("sensor.test_mqtt_bridge")
    assert s is not None
    assert s["state"] == "42.5"


@pytest.mark.asyncio
async def test_mqtt_binary_sensor_bridges():
    """Binary sensor MQTT publish bridges correctly."""
    mqtt_publish("home/binary_sensor/test_mqtt_motion/state", "on")
    await asyncio.sleep(0.3)

    s = await get_state("binary_sensor.test_mqtt_motion")
    assert s is not None
    assert s["state"] == "on"


@pytest.mark.asyncio
async def test_mqtt_update_preserves_attributes():
    """MQTT state update preserves existing attributes set via REST."""
    await set_state("sensor.test_mqtt_attrs", "10", {"unit_of_measurement": "°F"})
    await asyncio.sleep(0.1)

    mqtt_publish("home/sensor/test_mqtt_attrs/state", "20")
    await asyncio.sleep(0.3)

    s = await get_state("sensor.test_mqtt_attrs")
    assert s["state"] == "20"
    assert s["attributes"]["unit_of_measurement"] == "°F"


@pytest.mark.asyncio
async def test_mqtt_triggers_automation():
    """MQTT state change should trigger automation engine."""
    # Precondition: locks locked, smoke detector off
    await set_state("lock.front_door", "locked")
    await set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.2)

    # Trigger smoke detector via MQTT
    mqtt_publish("home/binary_sensor/smoke_detector/state", "on")
    await asyncio.sleep(0.5)

    # Automation should have fired: locks unlocked
    front = await get_state("lock.front_door")
    assert front["state"] == "unlocked", "Smoke emergency should unlock front door via MQTT trigger"
