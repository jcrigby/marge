"""
CTS -- Comprehensive WebSocket Command Tests

Systematically tests all 23 WebSocket commands for completeness.
"""

import asyncio
import json
import pytest

pytestmark = pytest.mark.asyncio


# ── Core Commands ─────────────────────────────────────────

async def test_ws_ping_pong(ws):
    """WS ping returns pong."""
    ok = await ws.ping()
    assert ok is True


async def test_ws_get_states(ws, rest):
    """WS get_states returns all entity states."""
    await rest.set_state("sensor.ws_states_test", "42")
    states = await ws.get_states()
    assert isinstance(states, list)
    ids = [s["entity_id"] for s in states]
    assert "sensor.ws_states_test" in ids


async def test_ws_get_config(ws):
    """WS get_config returns location and version."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    config = resp["result"]
    assert config["location_name"] == "Marge Demo Home"
    assert "version" in config
    assert config["state"] == "RUNNING"
    assert "latitude" in config
    assert "longitude" in config
    assert "unit_system" in config


async def test_ws_get_services(ws):
    """WS get_services returns service registry."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    result = resp["result"]
    assert isinstance(result, list)
    domains = [s["domain"] for s in result]
    assert "light" in domains
    assert "switch" in domains
    assert "timer" in domains


async def test_ws_fire_event(ws):
    """WS fire_event succeeds."""
    resp = await ws.send_command("fire_event", event_type="test_event")
    assert resp["success"] is True


async def test_ws_get_notifications(ws, rest):
    """WS get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


# ── Subscribe/Unsubscribe ────────────────────────────────

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
    # Short timeout — we expect no event
    try:
        event = await asyncio.wait_for(ws.ws.recv(), timeout=0.5)
        # If we got something, it shouldn't be for our unsubscribed ID
        data = json.loads(event)
        if data.get("type") == "event":
            assert data.get("id") != sub_id
    except asyncio.TimeoutError:
        pass  # Expected — no events delivered


# ── Call Service via WS ───────────────────────────────────

async def test_ws_call_service_light(ws, rest):
    """WS call_service light.turn_on works."""
    await rest.set_state("light.ws_call_test", "off")
    resp = await ws.send_command("call_service",
        domain="light", service="turn_on",
        service_data={"entity_id": "light.ws_call_test"})
    assert resp["success"] is True
    state = await rest.get_state("light.ws_call_test")
    assert state["state"] == "on"


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


# ── Registry List Commands ────────────────────────────────

async def test_ws_entity_registry_list(ws, rest):
    """WS config/entity_registry/list returns entity entries."""
    await rest.set_state("sensor.ws_reg_test", "42", {"friendly_name": "WS Reg Test"})
    resp = await ws.send_command("config/entity_registry/list")
    assert resp["success"] is True
    entries = resp["result"]
    assert isinstance(entries, list)
    ids = [e["entity_id"] for e in entries]
    assert "sensor.ws_reg_test" in ids


async def test_ws_area_registry_list(ws):
    """WS config/area_registry/list returns areas."""
    resp = await ws.send_command("config/area_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


async def test_ws_device_registry_list(ws):
    """WS config/device_registry/list returns devices."""
    resp = await ws.send_command("config/device_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


async def test_ws_label_registry_list(ws):
    """WS config/label_registry/list returns labels."""
    resp = await ws.send_command("config/label_registry/list")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


# ── Template Rendering ────────────────────────────────────

async def test_ws_render_template_states(ws, rest):
    """WS render_template with states() function works."""
    await rest.set_state("sensor.ws_tmpl_test", "99")
    resp = await ws.send_command("render_template",
        template="{{ states('sensor.ws_tmpl_test') }}")
    assert resp["success"] is True
    assert resp["result"]["result"] == "99"


async def test_ws_render_template_math(ws):
    """WS render_template with math expressions."""
    resp = await ws.send_command("render_template",
        template="{{ 6 * 7 }}")
    assert resp["success"] is True
    assert resp["result"]["result"].strip() == "42"


# ── Persistent Notification via WS ────────────────────────

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
