"""CTS -- MQTT bridge tests.

Tests that MQTT publishes to Marge's embedded broker
are bridged into the state machine and trigger automations.
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


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"cts-{topic.replace('/', '-')[:18]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
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


# ── Merged from test_mqtt_bridge_depth.py ────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("domain,entity_name,payload,expected_state", [
    ("alarm_control_panel", "test_bdep_alarm", "armed_home", "armed_home"),
    ("fan", "test_bdep_fan", "on", "on"),
    ("media_player", "test_bdep_mp", "playing", "playing"),
    ("vacuum", "test_bdep_vac", "cleaning", "cleaning"),
    ("input_boolean", "test_bdep_ib", "on", "on"),
], ids=["alarm-panel", "fan", "media-player", "vacuum", "input-boolean"])
async def test_mqtt_domain_bridge(domain, entity_name, payload, expected_state):
    """MQTT state bridge works for various domains."""
    mqtt_publish(f"home/{domain}/{entity_name}/state", payload)
    await asyncio.sleep(0.3)
    s = await get_state(f"{domain}.{entity_name}")
    assert s is not None
    assert s["state"] == expected_state


@pytest.mark.asyncio
async def test_mqtt_state_overwrite():
    """MQTT message overwrites existing state."""
    mqtt_publish("home/sensor/test_bdep_overwrite/state", "first")
    await asyncio.sleep(0.3)
    mqtt_publish("home/sensor/test_bdep_overwrite/state", "second")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_overwrite")
    assert s["state"] == "second"


@pytest.mark.asyncio
async def test_mqtt_state_preserves_multiple_rest_attrs():
    """MQTT state update preserves multiple attributes set via REST."""
    await set_state("sensor.test_bdep_preserve", "10", {"location": "kitchen", "type": "temp"})
    await asyncio.sleep(0.1)
    mqtt_publish("home/sensor/test_bdep_preserve/state", "20")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_preserve")
    assert s["state"] == "20"
    assert s["attributes"]["location"] == "kitchen"
    assert s["attributes"]["type"] == "temp"


@pytest.mark.asyncio
async def test_mqtt_unicode_payload():
    """MQTT bridge handles unicode payloads."""
    mqtt_publish("home/sensor/test_bdep_unicode/state", "23.5\u00b0C")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_unicode")
    assert s["state"] == "23.5\u00b0C"


@pytest.mark.asyncio
async def test_mqtt_empty_payload():
    """MQTT empty payload sets empty string state."""
    mqtt_publish("home/sensor/test_bdep_empty/state", "")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_empty")
    assert s is not None
    assert s["state"] == ""


@pytest.mark.asyncio
async def test_mqtt_sets_timestamps():
    """MQTT state change sets last_changed and last_updated."""
    mqtt_publish("home/sensor/test_bdep_ts/state", "with_timestamps")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_ts")
    assert s is not None
    assert "last_changed" in s
    assert "last_updated" in s
    assert len(s["last_changed"]) > 0
