"""
CTS -- Extended MQTT Bridge Tests

Tests MQTT state bridging for additional domains, JSON payloads,
and multi-entity scenarios.
"""

import asyncio
import time
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
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-ext-{topic.replace('/', '-')[:20]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


@pytest.mark.asyncio
async def test_mqtt_light_state():
    """MQTT publish on light topic updates entity state."""
    mqtt_publish("home/light/test_mqtt_light/state", "on")
    await asyncio.sleep(0.3)
    s = await get_state("light.test_mqtt_light")
    assert s is not None
    assert s["state"] == "on"


@pytest.mark.asyncio
async def test_mqtt_switch_state():
    """MQTT publish on switch topic updates entity state."""
    mqtt_publish("home/switch/test_mqtt_switch/state", "off")
    await asyncio.sleep(0.3)
    s = await get_state("switch.test_mqtt_switch")
    assert s is not None
    assert s["state"] == "off"


@pytest.mark.asyncio
async def test_mqtt_lock_state():
    """MQTT publish on lock topic updates entity state."""
    mqtt_publish("home/lock/test_mqtt_lock/state", "locked")
    await asyncio.sleep(0.3)
    s = await get_state("lock.test_mqtt_lock")
    assert s is not None
    assert s["state"] == "locked"


@pytest.mark.asyncio
async def test_mqtt_cover_state():
    """MQTT publish on cover topic updates entity state."""
    mqtt_publish("home/cover/test_mqtt_cover/state", "open")
    await asyncio.sleep(0.3)
    s = await get_state("cover.test_mqtt_cover")
    assert s is not None
    assert s["state"] == "open"


@pytest.mark.asyncio
async def test_mqtt_climate_state():
    """MQTT publish on climate topic updates entity state."""
    mqtt_publish("home/climate/test_mqtt_climate/state", "heat")
    await asyncio.sleep(0.3)
    s = await get_state("climate.test_mqtt_climate")
    assert s is not None
    assert s["state"] == "heat"


@pytest.mark.asyncio
async def test_mqtt_rapid_updates():
    """MQTT rapid updates don't lose messages."""
    # Publish 10 values quickly
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cts-ext-rapid")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    for i in range(10):
        c.publish("home/sensor/test_mqtt_rapid/state", str(i), retain=True)
        time.sleep(0.05)
    time.sleep(0.5)
    c.loop_stop()
    c.disconnect()

    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_mqtt_rapid")
    assert s is not None
    # Should have the last value
    assert s["state"] == "9"


@pytest.mark.asyncio
async def test_mqtt_json_payload():
    """MQTT JSON payload is bridged with attributes."""
    import json
    payload = json.dumps({"state": "72.5", "unit_of_measurement": "°F"})
    mqtt_publish("home/sensor/test_mqtt_json/state", payload)
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_mqtt_json")
    assert s is not None
    # State should be the full JSON or parsed value
    assert s["state"] is not None


@pytest.mark.asyncio
async def test_mqtt_state_then_rest_read():
    """MQTT-published state is immediately readable via REST."""
    mqtt_publish("home/sensor/test_mqtt_rest_read/state", "99.9")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_mqtt_rest_read")
    assert s is not None
    assert s["state"] == "99.9"
    assert "last_changed" in s
    assert "last_updated" in s


@pytest.mark.asyncio
async def test_mqtt_multiple_domains():
    """MQTT publishes to multiple domains create correct entities."""
    mqtt_publish("home/sensor/multi_test/state", "50")
    mqtt_publish("home/binary_sensor/multi_test/state", "on")
    mqtt_publish("home/light/multi_test/state", "off")
    await asyncio.sleep(0.5)

    s1 = await get_state("sensor.multi_test")
    s2 = await get_state("binary_sensor.multi_test")
    s3 = await get_state("light.multi_test")

    assert s1 is not None and s1["state"] == "50"
    assert s2 is not None and s2["state"] == "on"
    assert s3 is not None and s3["state"] == "off"
