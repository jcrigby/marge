"""
CTS -- WebSocket Integration & Cross-System Tests

Consolidated tests for:
  - WebSocket command coverage (get_services, subscribe, call_service, etc.)
  - MQTT -> REST -> WS roundtrip integration
  - Concurrent WS + REST operations (thread safety)
"""

import asyncio
import json
import os
import time
import uuid

import httpx
import paho.mqtt.client as mqtt
import pytest

pytestmark = pytest.mark.asyncio

# ── SUT Config (mirrors conftest defaults) ───────────────
_SUT_URL = os.environ.get("SUT_URL", "http://localhost:8124")
_SUT_MQTT_HOST = os.environ.get("SUT_MQTT_HOST", "localhost")
_SUT_MQTT_PORT = int(os.environ.get("SUT_MQTT_PORT", "1883"))
_HEADERS = {
    "Authorization": f"Bearer {os.environ.get('SUT_TOKEN', 'test-token')}",
    "Content-Type": "application/json",
}


# ── Helpers ──────────────────────────────────────────────

def mqtt_publish(topic: str, payload: str):
    """Publish a single retained message to the SUT MQTT broker."""
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cts-rt-{uuid.uuid4().hex[:8]}")
    c.connect(_SUT_MQTT_HOST, _SUT_MQTT_PORT, keepalive=10)
    c.loop_start()
    c.publish(topic, payload, retain=True)
    time.sleep(0.3)
    c.loop_stop()
    c.disconnect()


# ═══════════════════════════════════════════════════════════
# SECTION 1: WebSocket Core Commands
# ═══════════════════════════════════════════════════════════

async def test_ws_get_services_has_service_names(ws):
    """get_services includes service names per domain."""
    resp = await ws.send_command("get_services")
    result = resp["result"]
    light = next(e for e in result if e["domain"] == "light")
    assert "turn_on" in light["services"]
    assert "turn_off" in light["services"]
    assert "toggle" in light["services"]


async def test_ws_get_notifications(ws, rest):
    """WS get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


# ── Subscribe / Unsubscribe ──────────────────────────────

async def test_ws_subscribe_and_receive(ws, rest):
    """WS subscribe_events receives state_changed events."""
    sub_id = await ws.subscribe_events("state_changed")
    assert sub_id > 0

    # Trigger a state change
    await rest.set_state("sensor.ws_sub_test", "changed")

    # Should receive the event
    event = await ws.recv_event(timeout=3.0)
    assert event["type"] == "event"
    assert event["event"]["event_type"] == "state_changed"


async def test_ws_unsubscribe(ws, rest):
    """WS unsubscribe_events stops delivering events for that subscription."""
    sub_id = await ws.subscribe_events("state_changed")

    # Unsubscribe
    resp = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert resp["success"] is True

    # State change should NOT produce an event on this subscription
    await rest.set_state("sensor.ws_unsub_test", "ignored")
    # Short timeout -- we expect no event
    try:
        event = await asyncio.wait_for(ws.ws.recv(), timeout=0.5)
        # If we got something, it shouldn't be for our unsubscribed ID
        data = json.loads(event)
        if data.get("type") == "event":
            assert data.get("id") != sub_id
    except asyncio.TimeoutError:
        pass  # Expected -- no events delivered


# ── Call Service via WS ──────────────────────────────────

async def test_ws_call_service_timer(ws, rest):
    """WS call_service timer.start works."""
    await rest.set_state("timer.ws_call_test", "idle")
    resp = await ws.send_command("call_service",
        domain="timer", service="start",
        service_data={"entity_id": "timer.ws_call_test"})
    assert resp["success"] is True
    state = await rest.get_state("timer.ws_call_test")
    assert state["state"] == "active"


async def test_ws_call_service_counter(ws, rest):
    """WS call_service counter.increment works."""
    await rest.set_state("counter.ws_call_test", "0")
    resp = await ws.send_command("call_service",
        domain="counter", service="increment",
        service_data={"entity_id": "counter.ws_call_test"})
    assert resp["success"] is True
    state = await rest.get_state("counter.ws_call_test")
    assert state["state"] == "1"


# ── Template Rendering ───────────────────────────────────

async def test_ws_render_template_states(ws, rest):
    """WS render_template with states() function works."""
    await rest.set_state("sensor.ws_tmpl_test", "99")
    resp = await ws.send_command("render_template",
        template="{{ states('sensor.ws_tmpl_test') }}")
    assert resp["success"] is True
    assert resp["result"]["result"] == "99"


# ── Persistent Notification via WS ───────────────────────

async def test_ws_notification_lifecycle(ws):
    """WS create, list, dismiss notification."""
    # Create
    resp = await ws.send_command("call_service",
        domain="persistent_notification", service="create",
        service_data={
            "notification_id": "ws_notif_test",
            "title": "Test",
            "message": "Hello from WS",
        })
    assert resp["success"] is True

    # List
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    notifs = resp["result"]
    ids = [n["notification_id"] for n in notifs]
    assert "ws_notif_test" in ids

    # Dismiss
    resp = await ws.send_command("persistent_notification/dismiss",
        notification_id="ws_notif_test")
    assert resp["success"] is True

    # Verify gone
    resp = await ws.send_command("get_notifications")
    ids = [n["notification_id"] for n in resp["result"]]
    assert "ws_notif_test" not in ids


# ═══════════════════════════════════════════════════════════
# SECTION 2: MQTT + REST + WS Roundtrip Integration
# ═══════════════════════════════════════════════════════════

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


@pytest.mark.parametrize("topic_template,entity_template", [
    ("other/sensor/bad_{tag}/state", "sensor.bad_{tag}"),       # wrong root prefix
    ("home/sensor/nofinal_{tag}", "sensor.nofinal_{tag}"),      # missing /state segment
], ids=["wrong_prefix", "missing_state_segment"])
async def test_mqtt_bad_topic_ignored(rest, topic_template, entity_template):
    """MQTT messages on invalid topics are ignored by state bridge."""
    tag = uuid.uuid4().hex[:8]
    mqtt_publish(topic_template.format(tag=tag), "should_not_exist")
    await asyncio.sleep(0.5)

    state = await rest.get_state(entity_template.format(tag=tag))
    assert state is None


# ═══════════════════════════════════════════════════════════
# SECTION 3: Concurrent WS + REST Operations
# ═══════════════════════════════════════════════════════════

async def test_parallel_state_sets_10(rest):
    """10 parallel state sets all succeed."""
    tag = uuid.uuid4().hex[:8]

    async def set_one(i):
        await rest.set_state(f"sensor.par_{tag}_{i}", str(i))

    await asyncio.gather(*[set_one(i) for i in range(10)])

    for i in range(10):
        state = await rest.get_state(f"sensor.par_{tag}_{i}")
        assert state is not None
        assert state["state"] == str(i)


async def test_parallel_service_calls(rest):
    """10 parallel service calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.par_svc_{tag}_{i}" for i in range(10)]

    for eid in entities:
        await rest.set_state(eid, "off")

    async def turn_on(eid):
        await rest.call_service("light", "turn_on", {"entity_id": eid})

    await asyncio.gather(*[turn_on(eid) for eid in entities])

    for eid in entities:
        assert (await rest.get_state(eid))["state"] == "on"


@pytest.mark.parametrize("path,params,count", [
    ("/api/states", None, 5),
    ("/api/health", None, 10),
    ("/api/states/search", {"domain": "light"}, 5),
], ids=["get_states", "health_checks", "search_requests"])
async def test_concurrent_get_endpoint(path, params, count):
    """Concurrent GET requests to the same endpoint all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.get(f"{_SUT_URL}{path}", params=params, headers=_HEADERS)
            for _ in range(count)
        ]
        results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200


async def test_mixed_read_write_concurrent(rest):
    """Concurrent reads and writes don't interfere."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mixed_{tag}"
    await rest.set_state(eid, "initial")

    async def writer():
        for i in range(5):
            await rest.set_state(eid, f"write_{i}")
            await asyncio.sleep(0.01)

    async def reader():
        for _ in range(5):
            state = await rest.get_state(eid)
            assert state is not None
            await asyncio.sleep(0.01)

    await asyncio.gather(writer(), reader())

    # Final state should be the last written value
    state = await rest.get_state(eid)
    assert state["state"] == "write_4"


async def test_concurrent_template_renders():
    """5 concurrent template renders all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{_SUT_URL}/api/template",
                json={"template": f"{{{{ {i} + {i} }}}}"},
                headers=_HEADERS,
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

    for i, r in enumerate(results):
        assert r.status_code == 200
        assert str(i * 2) in r.text
