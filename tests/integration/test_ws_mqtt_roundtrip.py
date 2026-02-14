"""
CTS -- WebSocket + MQTT Roundtrip Integration Tests

Tests end-to-end flow: publish state via MQTT home/# bridge,
verify entity appears via REST, verify state_changed event
is delivered to WebSocket subscribers.
"""

import asyncio
import json
import time
import uuid

import paho.mqtt.client as mqtt
import pytest

MQTT_HOST = "localhost"
MQTT_PORT = 1884

pytestmark = pytest.mark.asyncio


def mqtt_publish(topic: str, payload: str):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-rt-{uuid.uuid4().hex[:8]}")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


async def test_mqtt_state_appears_in_rest(rest):
    """MQTT publish on home/domain/id/state creates entity in REST."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"home/sensor/mqtt_rt_{tag}/state", "42")
    await asyncio.sleep(0.5)

    state = await rest.get_state(f"sensor.mqtt_rt_{tag}")
    assert state is not None
    assert state["state"] == "42"


async def test_mqtt_state_triggers_ws_event(ws, rest):
    """MQTT state publish triggers state_changed event on WebSocket."""
    tag = uuid.uuid4().hex[:8]
    entity_id = f"sensor.mqtt_ws_rt_{tag}"

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    assert sub.get("success") is True
    sub_id = sub["id"]

    mqtt_publish(f"home/sensor/mqtt_ws_rt_{tag}/state", "hello")

    found = False
    for _ in range(50):
        try:
            msg = await ws.recv_event(timeout=2.0)
        except asyncio.TimeoutError:
            break
        if msg.get("type") == "event":
            data = msg["event"].get("data", {})
            if data.get("entity_id") == entity_id:
                assert data["new_state"]["state"] == "hello"
                found = True
                break
    assert found, f"Did not receive state_changed for {entity_id}"

    await ws.send_command("unsubscribe_events", subscription=sub_id)


async def test_mqtt_update_triggers_ws_with_old_state(ws, rest):
    """Second MQTT publish includes old_state in WS event."""
    tag = uuid.uuid4().hex[:8]
    entity_id = f"sensor.mqtt_old_{tag}"

    # Create initial state
    mqtt_publish(f"home/sensor/mqtt_old_{tag}/state", "first")
    await asyncio.sleep(0.5)

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    sub_id = sub["id"]

    mqtt_publish(f"home/sensor/mqtt_old_{tag}/state", "second")

    found = False
    for _ in range(50):
        try:
            msg = await ws.recv_event(timeout=2.0)
        except asyncio.TimeoutError:
            break
        if msg.get("type") == "event":
            data = msg["event"].get("data", {})
            if data.get("entity_id") == entity_id:
                assert data["old_state"] is not None
                assert data["old_state"]["state"] == "first"
                assert data["new_state"]["state"] == "second"
                found = True
                break
    assert found

    await ws.send_command("unsubscribe_events", subscription=sub_id)


async def test_mqtt_multiple_domains(rest):
    """MQTT bridge handles multiple domains correctly."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"home/sensor/md_{tag}/state", "25.0")
    mqtt_publish(f"home/binary_sensor/md_{tag}/state", "on")
    mqtt_publish(f"home/switch/md_{tag}/state", "off")
    await asyncio.sleep(0.5)

    s1 = await rest.get_state(f"sensor.md_{tag}")
    assert s1 is not None
    assert s1["state"] == "25.0"

    s2 = await rest.get_state(f"binary_sensor.md_{tag}")
    assert s2 is not None
    assert s2["state"] == "on"

    s3 = await rest.get_state(f"switch.md_{tag}")
    assert s3 is not None
    assert s3["state"] == "off"


async def test_mqtt_state_update_preserves_attributes(rest):
    """MQTT state update preserves existing entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqtt_attr_{tag}"

    # Set via REST with attributes first
    await rest.set_state(eid, "10", {"unit": "C", "device_class": "temperature"})

    # Update via MQTT (state only, no attributes in payload)
    mqtt_publish(f"home/sensor/mqtt_attr_{tag}/state", "20")
    await asyncio.sleep(0.5)

    state = await rest.get_state(eid)
    assert state["state"] == "20"
    assert state["attributes"].get("unit") == "C"
    assert state["attributes"].get("device_class") == "temperature"


async def test_mqtt_rapid_updates_all_recorded(rest):
    """Rapid MQTT updates are all recorded in state machine."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqtt_rapid_{tag}"

    for i in range(5):
        mqtt_publish(f"home/sensor/mqtt_rapid_{tag}/state", str(i))
    await asyncio.sleep(1.0)

    state = await rest.get_state(eid)
    assert state is not None
    # Final state should be the last published value
    assert state["state"] == "4"


async def test_mqtt_invalid_topic_ignored(rest):
    """MQTT messages on non-home topics are ignored by state bridge."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(f"other/sensor/bad_{tag}/state", "should_not_exist")
    await asyncio.sleep(0.5)

    state = await rest.get_state(f"sensor.bad_{tag}")
    assert state is None


async def test_mqtt_wrong_format_ignored(rest):
    """MQTT messages with wrong topic format ignored."""
    tag = uuid.uuid4().hex[:8]
    # Missing the trailing /state segment
    mqtt_publish(f"home/sensor/nofinal_{tag}", "nostate")
    await asyncio.sleep(0.5)

    state = await rest.get_state(f"sensor.nofinal_{tag}")
    assert state is None
