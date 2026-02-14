"""
CTS -- MQTT Broker Lifecycle and Topic Routing Tests

Tests embedded rumqttd broker connectivity, publish/subscribe
semantics, topic routing for home/# namespace, and connection
handling on port 1884.
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


def make_client(tag=""):
    cid = f"cts-bl-{tag or uuid.uuid4().hex[:8]}"
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)


async def test_broker_accepts_connection():
    """Embedded MQTT broker accepts TCP connections on port 1884."""
    c = make_client("conn")
    result = c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    assert result == 0
    c.disconnect()


async def test_publish_and_subscribe():
    """Publish + subscribe roundtrip on embedded broker."""
    tag = uuid.uuid4().hex[:8]
    topic = f"test/roundtrip/{tag}"
    received = []

    def on_message(_client, _userdata, msg):
        received.append(msg.payload.decode())

    sub = make_client("sub")
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    sub.subscribe(topic, qos=0)
    sub.loop_start()

    await asyncio.sleep(0.3)

    pub = make_client("pub")
    pub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    pub.loop_start()
    pub.publish(topic, "hello", retain=False)

    await asyncio.sleep(0.5)

    pub.loop_stop()
    pub.disconnect()
    sub.loop_stop()
    sub.disconnect()

    assert "hello" in received


async def test_retained_message_delivery():
    """Retained messages are delivered to late subscribers."""
    tag = uuid.uuid4().hex[:8]
    topic = f"test/retain/{tag}"
    received = []

    # Publish with retain FIRST
    pub = make_client("retpub")
    pub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    pub.loop_start()
    pub.publish(topic, "retained_value", retain=True)
    await asyncio.sleep(0.3)
    pub.loop_stop()
    pub.disconnect()

    # Subscribe AFTER publish
    def on_message(_client, _userdata, msg):
        received.append(msg.payload.decode())

    sub = make_client("retsub")
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    sub.subscribe(topic, qos=0)
    sub.loop_start()
    await asyncio.sleep(0.5)
    sub.loop_stop()
    sub.disconnect()

    assert "retained_value" in received


async def test_wildcard_subscription():
    """Wildcard # subscription receives messages from sub-topics."""
    tag = uuid.uuid4().hex[:8]
    received = []

    def on_message(_client, _userdata, msg):
        received.append(msg.topic)

    sub = make_client("wildsub")
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    sub.subscribe(f"test/wild/{tag}/#", qos=0)
    sub.loop_start()
    await asyncio.sleep(0.3)

    pub = make_client("wildpub")
    pub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    pub.loop_start()
    pub.publish(f"test/wild/{tag}/a", "1")
    pub.publish(f"test/wild/{tag}/b/c", "2")
    await asyncio.sleep(0.5)

    pub.loop_stop()
    pub.disconnect()
    sub.loop_stop()
    sub.disconnect()

    topics = received
    assert any(f"test/wild/{tag}/a" in t for t in topics)
    assert any(f"test/wild/{tag}/b/c" in t for t in topics)


async def test_multiple_clients_concurrent():
    """Multiple concurrent clients can connect and publish."""
    tag = uuid.uuid4().hex[:8]
    received = []

    def on_message(_client, _userdata, msg):
        received.append(msg.payload.decode())

    sub = make_client("mcsub")
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    sub.subscribe(f"test/multi/{tag}/#", qos=0)
    sub.loop_start()
    await asyncio.sleep(0.3)

    clients = []
    for i in range(5):
        c = make_client(f"mc{i}")
        c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
        c.loop_start()
        c.publish(f"test/multi/{tag}/{i}", f"msg_{i}")
        clients.append(c)

    await asyncio.sleep(1.0)

    for c in clients:
        c.loop_stop()
        c.disconnect()
    sub.loop_stop()
    sub.disconnect()

    assert len(received) >= 5


async def test_home_topic_state_bridge(rest):
    """home/domain/id/state topic bridges to entity state."""
    tag = uuid.uuid4().hex[:8]
    c = make_client("bridge")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(f"home/sensor/broker_test_{tag}/state", "99.5", retain=True)
    await asyncio.sleep(0.5)
    c.loop_stop()
    c.disconnect()

    state = await rest.get_state(f"sensor.broker_test_{tag}")
    assert state is not None
    assert state["state"] == "99.5"


async def test_non_home_topic_no_entity(rest):
    """Non-home/ topics do not create entities in state machine."""
    tag = uuid.uuid4().hex[:8]
    c = make_client("noent")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(f"custom/sensor/noent_{tag}/state", "value", retain=True)
    await asyncio.sleep(0.5)
    c.loop_stop()
    c.disconnect()

    state = await rest.get_state(f"sensor.noent_{tag}")
    assert state is None


async def test_disconnect_reconnect():
    """Client can disconnect and reconnect cleanly."""
    c = make_client("reconn")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    await asyncio.sleep(0.1)
    c.loop_stop()
    c.disconnect()

    await asyncio.sleep(0.2)

    c2 = make_client("reconn2")
    result = c2.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    assert result == 0
    c2.disconnect()


async def test_json_payload_publish():
    """JSON payloads publish and deliver correctly."""
    tag = uuid.uuid4().hex[:8]
    topic = f"test/json/{tag}"
    received = []

    def on_message(_client, _userdata, msg):
        received.append(json.loads(msg.payload.decode()))

    sub = make_client("jsonsub")
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    sub.subscribe(topic, qos=0)
    sub.loop_start()
    await asyncio.sleep(0.3)

    payload = json.dumps({"temperature": 22.5, "humidity": 45})
    pub = make_client("jsonpub")
    pub.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    pub.loop_start()
    pub.publish(topic, payload)
    await asyncio.sleep(0.5)

    pub.loop_stop()
    pub.disconnect()
    sub.loop_stop()
    sub.disconnect()

    assert len(received) >= 1
    assert received[0]["temperature"] == 22.5


async def test_empty_payload_publish():
    """Empty payload publishes without error."""
    tag = uuid.uuid4().hex[:8]
    c = make_client("empty")
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    c.loop_start()
    info = c.publish(f"test/empty/{tag}", "", retain=False)
    info.wait_for_publish(timeout=5)
    assert info.rc == 0
    c.loop_stop()
    c.disconnect()
