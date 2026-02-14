"""
CTS -- End-to-End Integration Tests

Tests that exercise multiple subsystems together: state + WS events,
service calls + state verification, discovery + service dispatch,
and full automation trigger chains.
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


def mqtt_publish(topic: str, payload: str, retain: bool = True):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-e2e-{topic.replace('/', '-')[:20]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=retain)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


pytestmark = pytest.mark.asyncio


async def test_set_state_and_read_back(rest):
    """Set state via REST and read it back."""
    await rest.set_state("sensor.e2e_roundtrip", "42", {"unit": "lux"})
    state = await rest.get_state("sensor.e2e_roundtrip")
    assert state["state"] == "42"
    assert state["attributes"]["unit"] == "lux"
    assert "entity_id" in state
    assert "last_changed" in state
    assert "context" in state


async def test_service_call_changes_state(rest):
    """Service call through REST changes entity state."""
    await rest.set_state("light.e2e_svc", "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.e2e_svc",
        "brightness": 200,
    })
    state = await rest.get_state("light.e2e_svc")
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_ws_receives_state_change(ws, rest):
    """WebSocket receives state_changed event from REST API."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.e2e_ws", "ping")
    event = await ws.recv_event(timeout=5.0)
    assert event["event"]["event_type"] == "state_changed"
    assert event["event"]["data"]["entity_id"] == "sensor.e2e_ws"
    assert event["event"]["data"]["new_state"]["state"] == "ping"


async def test_discovery_creates_entity_then_service_controls():
    """MQTT discovery creates entity, then REST service controls it."""
    # Discover a switch
    config = json.dumps({
        "name": "E2E Switch",
        "unique_id": "e2e_sw_001",
        "state_topic": "home/switch/e2e_sw/state",
        "command_topic": "home/switch/e2e_sw/set",
    })
    mqtt_publish("homeassistant/switch/e2e_sw/config", config)
    await asyncio.sleep(0.5)

    # Verify entity was created
    state = await get_state("switch.e2e_sw")
    assert state is not None
    assert state["state"] == "off"

    # Turn on via REST service
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE}/api/services/switch/turn_on",
            json={"entity_id": "switch.e2e_sw"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    state = await get_state("switch.e2e_sw")
    assert state["state"] == "on"


async def test_mqtt_bridge_updates_state():
    """MQTT publish on home/domain/object_id/state updates entity."""
    mqtt_publish("home/sensor/e2e_mqtt_bridge/state", "73.5")
    await asyncio.sleep(0.5)

    state = await get_state("sensor.e2e_mqtt_bridge")
    assert state is not None
    assert state["state"] == "73.5"


async def test_discovery_state_update_with_template():
    """Discovery entity processes state update with value_template."""
    config = json.dumps({
        "name": "E2E Temp Sensor",
        "unique_id": "e2e_temp_tmpl",
        "state_topic": "sensors/e2e_temp_tmpl/data",
        "value_template": "{{ value_json.temperature }}",
    })
    mqtt_publish("homeassistant/sensor/e2e_temp_tmpl/config", config)
    await asyncio.sleep(0.5)

    # Send JSON payload to state topic
    mqtt_publish("sensors/e2e_temp_tmpl/data", '{"temperature": 21.5, "humidity": 55}')
    await asyncio.sleep(0.5)

    state = await get_state("sensor.e2e_temp_tmpl")
    assert state is not None
    assert state["state"] == "21.5"


async def test_automation_trigger_fires_actions(rest):
    """State change triggers automation that fires actions."""
    # smoke_co_emergency triggers on binary_sensor.smoke_detector -> on
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.2)

    s1 = await rest.get_state("automation.smoke_co_emergency")
    count_before = s1["attributes"].get("current", 0)

    # Trigger
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.smoke_co_emergency")
    count_after = s2["attributes"].get("current", 0)
    assert count_after > count_before


async def test_scene_activation_multiple_entities(rest):
    """Scene activation sets multiple entity states at once."""
    # Reset states
    for eid in ["light.living_room_main", "light.living_room_accent",
                "light.living_room_lamp", "light.living_room_floor"]:
        await rest.set_state(eid, "off")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening"
    })
    await asyncio.sleep(0.3)

    # All should be on with correct brightness
    for eid in ["light.living_room_main", "light.living_room_accent",
                "light.living_room_lamp", "light.living_room_floor"]:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on after evening scene"


async def test_health_after_operations(rest):
    """Health endpoint reflects accumulated metrics."""
    health = await rest.get_health()
    assert health["state_changes"] > 0
    assert health["events_fired"] > 0
    assert health["entity_count"] > 0
    assert health["latency_avg_us"] > 0
