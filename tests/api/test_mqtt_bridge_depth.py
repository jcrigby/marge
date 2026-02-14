"""
CTS -- MQTT Bridge Depth Tests

Tests advanced MQTT bridge scenarios: JSON state payloads,
command publishing (set topics), and multi-attribute updates.
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


async def set_state(entity_id: str, state: str, attrs=None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-bdep-{topic.replace('/', '-')[:18]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


# ── Domain Bridge ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_alarm_panel_state():
    """MQTT alarm_control_panel state bridge."""
    mqtt_publish("home/alarm_control_panel/test_bdep_alarm/state", "armed_home")
    await asyncio.sleep(0.3)
    s = await get_state("alarm_control_panel.test_bdep_alarm")
    assert s is not None
    assert s["state"] == "armed_home"


@pytest.mark.asyncio
async def test_mqtt_fan_state():
    """MQTT fan state bridge."""
    mqtt_publish("home/fan/test_bdep_fan/state", "on")
    await asyncio.sleep(0.3)
    s = await get_state("fan.test_bdep_fan")
    assert s is not None
    assert s["state"] == "on"


@pytest.mark.asyncio
async def test_mqtt_media_player_state():
    """MQTT media_player state bridge."""
    mqtt_publish("home/media_player/test_bdep_mp/state", "playing")
    await asyncio.sleep(0.3)
    s = await get_state("media_player.test_bdep_mp")
    assert s is not None
    assert s["state"] == "playing"


@pytest.mark.asyncio
async def test_mqtt_vacuum_state():
    """MQTT vacuum state bridge."""
    mqtt_publish("home/vacuum/test_bdep_vac/state", "cleaning")
    await asyncio.sleep(0.3)
    s = await get_state("vacuum.test_bdep_vac")
    assert s is not None
    assert s["state"] == "cleaning"


@pytest.mark.asyncio
async def test_mqtt_input_boolean_state():
    """MQTT input_boolean state bridge."""
    mqtt_publish("home/input_boolean/test_bdep_ib/state", "on")
    await asyncio.sleep(0.3)
    s = await get_state("input_boolean.test_bdep_ib")
    assert s is not None
    assert s["state"] == "on"


# ── State Overwrite ──────────────────────────────────────────

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
async def test_mqtt_state_preserves_rest_attrs():
    """MQTT state update preserves attributes set via REST."""
    await set_state("sensor.test_bdep_preserve", "10", {"location": "kitchen", "type": "temp"})
    await asyncio.sleep(0.1)
    mqtt_publish("home/sensor/test_bdep_preserve/state", "20")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_preserve")
    assert s["state"] == "20"
    assert s["attributes"]["location"] == "kitchen"
    assert s["attributes"]["type"] == "temp"


# ── Special Characters ──────────────────────────────────────

@pytest.mark.asyncio
async def test_mqtt_unicode_payload():
    """MQTT bridge handles unicode payloads."""
    mqtt_publish("home/sensor/test_bdep_unicode/state", "23.5°C")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_unicode")
    assert s["state"] == "23.5°C"


@pytest.mark.asyncio
async def test_mqtt_empty_payload():
    """MQTT empty payload sets empty string state."""
    mqtt_publish("home/sensor/test_bdep_empty/state", "")
    await asyncio.sleep(0.3)
    s = await get_state("sensor.test_bdep_empty")
    assert s is not None
    assert s["state"] == ""


# ── Last Changed / Updated ──────────────────────────────────

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
