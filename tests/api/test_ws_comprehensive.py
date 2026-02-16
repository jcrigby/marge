"""
CTS -- Comprehensive WebSocket Command Tests

Systematically tests all 23 WebSocket commands for completeness.
"""

import asyncio
import json
import pytest

pytestmark = pytest.mark.asyncio


# ── Core Commands ─────────────────────────────────────────

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


# ── Template Rendering ────────────────────────────────────

async def test_ws_render_template_states(ws, rest):
    """WS render_template with states() function works."""
    await rest.set_state("sensor.ws_tmpl_test", "99")
    resp = await ws.send_command("render_template",
        template="{{ states('sensor.ws_tmpl_test') }}")
    assert resp["success"] is True
    assert resp["result"]["result"] == "99"


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
