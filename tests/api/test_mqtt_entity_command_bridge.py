"""
CTS -- MQTT Entity Command Bridge Tests

Tests the embedded MQTT broker's home/# topic bridge: publishing to
home/{domain}/{object_id}/state creates or updates entities, verifying
the topic_to_entity_id mapping and state machine integration.
Uses the external MQTT port (1884) on the Marge container.
"""

import asyncio
import json
import time
import uuid
import pytest
import paho.mqtt.client as mqtt

pytestmark = pytest.mark.asyncio

MQTT_HOST = "localhost"
MQTT_PORT = 1884


def _publish_and_wait(topic: str, payload: str, wait: float = 0.5):
    """Publish a message to Marge's embedded MQTT broker."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"cts-mqtt-{uuid.uuid4().hex[:8]}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    client.loop_start()
    client.publish(topic, payload, qos=0)
    time.sleep(wait)
    client.loop_stop()
    client.disconnect()


async def test_mqtt_state_topic_creates_entity(rest):
    """Publishing to home/{domain}/{id}/state creates entity."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/sensor/mqtt_test_{tag}/state", "42")

    state = await rest.get_state(f"sensor.mqtt_test_{tag}")
    assert state is not None
    assert state["state"] == "42"


async def test_mqtt_binary_sensor_state(rest):
    """Publishing to home/binary_sensor/x/state creates binary_sensor."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/binary_sensor/mqtt_bs_{tag}/state", "on")

    state = await rest.get_state(f"binary_sensor.mqtt_bs_{tag}")
    assert state is not None
    assert state["state"] == "on"


async def test_mqtt_switch_state(rest):
    """Publishing to home/switch/x/state creates switch entity."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/switch/mqtt_sw_{tag}/state", "off")

    state = await rest.get_state(f"switch.mqtt_sw_{tag}")
    assert state is not None
    assert state["state"] == "off"


async def test_mqtt_state_update_preserves_attributes(rest):
    """MQTT state update preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqtt_attr_{tag}"
    # Set entity with attributes via REST
    await rest.set_state(eid, "initial", {"unit": "C", "friendly_name": "MQTT Test"})

    # Update via MQTT
    _publish_and_wait(f"home/sensor/mqtt_attr_{tag}/state", "updated")

    state = await rest.get_state(eid)
    assert state["state"] == "updated"
    assert state["attributes"].get("unit") == "C"
    assert state["attributes"].get("friendly_name") == "MQTT Test"


async def test_mqtt_sequential_updates(rest):
    """Multiple MQTT updates result in last value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mqtt_seq_{tag}"
    for i in range(5):
        _publish_and_wait(f"home/sensor/mqtt_seq_{tag}/state", str(i), wait=0.2)

    state = await rest.get_state(eid)
    assert state["state"] == "4"


async def test_mqtt_non_state_topic_ignored(rest):
    """Topics not matching home/+/+/state are ignored."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/sensor/mqtt_cmd_{tag}/command", "value")

    # Entity should NOT be created
    state = await rest.get_state(f"sensor.mqtt_cmd_{tag}")
    assert state is None


async def test_mqtt_light_domain(rest):
    """Publishing to home/light/x/state creates light entity."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/light/mqtt_lt_{tag}/state", "on")

    state = await rest.get_state(f"light.mqtt_lt_{tag}")
    assert state is not None
    assert state["state"] == "on"


async def test_mqtt_numeric_state(rest):
    """MQTT numeric state stored as string."""
    tag = uuid.uuid4().hex[:8]
    _publish_and_wait(f"home/sensor/mqtt_num_{tag}/state", "98.6")

    state = await rest.get_state(f"sensor.mqtt_num_{tag}")
    assert state["state"] == "98.6"


async def test_mqtt_state_triggers_automation(rest):
    """MQTT state update can trigger state-based automations."""
    # Set up: ensure smoke_co_emergency is enabled, door locked
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await rest.set_state("lock.front_door", "locked")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency"
    })
    await asyncio.sleep(0.1)

    # Trigger via MQTT
    _publish_and_wait(
        "home/binary_sensor/smoke_detector/state", "on", wait=1.0
    )

    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"
