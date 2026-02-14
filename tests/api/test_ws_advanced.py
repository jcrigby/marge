"""
CTS -- Advanced WebSocket Command Tests

Tests render_template, fire_event, call_service edge cases,
unsubscribe_events, persistent_notification, and WS command
validation via WebSocket protocol.
"""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


# ── Render Template via WS ───────────────────────────────────

async def test_ws_render_template_simple(ws):
    """render_template returns rendered string."""
    result = await ws.send_command(
        "render_template",
        template="{{ 1 + 2 }}",
    )
    assert result["success"] is True
    assert "3" in str(result["result"])


async def test_ws_render_template_state_function(ws, rest):
    """render_template can access entity states."""
    await rest.set_state("sensor.ws_tmpl_test", "42")
    result = await ws.send_command(
        "render_template",
        template="{{ states('sensor.ws_tmpl_test') }}",
    )
    assert result["success"] is True
    assert "42" in str(result["result"])


async def test_ws_render_template_filter(ws):
    """render_template supports Jinja filters."""
    result = await ws.send_command(
        "render_template",
        template="{{ 'hello world' | upper }}",
    )
    assert result["success"] is True
    assert "HELLO WORLD" in str(result["result"])


async def test_ws_render_template_math(ws):
    """render_template evaluates math expressions."""
    result = await ws.send_command(
        "render_template",
        template="{{ (100 / 3) | round(1) }}",
    )
    assert result["success"] is True
    assert "33.3" in str(result["result"])


# ── Fire Event via WS ────────────────────────────────────────

async def test_ws_fire_event_returns_success(ws):
    """fire_event via WS returns success."""
    result = await ws.send_command(
        "fire_event",
        event_type="cts_ws_fire_test",
        event_data={"key": "value"},
    )
    assert result["success"] is True


async def test_ws_fire_event_no_data(ws):
    """fire_event with no event_data succeeds."""
    result = await ws.send_command(
        "fire_event",
        event_type="cts_ws_fire_nodata",
    )
    assert result["success"] is True


# ── Call Service via WS ──────────────────────────────────────

async def test_ws_call_service_with_data(ws, rest):
    """call_service via WS passes service_data through."""
    await rest.set_state("climate.ws_svc_data", "off")
    result = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={
            "entity_id": "climate.ws_svc_data",
            "temperature": 72,
        },
    )
    assert result["success"] is True
    state = await rest.get_state("climate.ws_svc_data")
    assert state["attributes"]["temperature"] == 72


async def test_ws_call_service_toggle(ws, rest):
    """call_service toggle via WS changes entity state."""
    await rest.set_state("switch.ws_toggle", "off")
    result = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": "switch.ws_toggle"},
    )
    assert result["success"] is True
    state = await rest.get_state("switch.ws_toggle")
    assert state["state"] == "on"


# ── Unsubscribe Events ──────────────────────────────────────

async def test_ws_unsubscribe_events(ws, rest):
    """unsubscribe_events stops event delivery."""
    sub_id = await ws.subscribe_events("state_changed")
    # Unsubscribe
    result = await ws.send_command(
        "unsubscribe_events",
        subscription=sub_id,
    )
    assert result["success"] is True
    # Change state — should NOT receive event
    await rest.set_state("sensor.ws_unsub_test", "changed")
    try:
        event = await ws.recv_event(timeout=0.5)
        # If we get here, verify it's NOT from our subscription
        assert event["id"] != sub_id
    except asyncio.TimeoutError:
        pass  # Expected — no event for unsubscribed


# ── Get Services via WS ─────────────────────────────────────

async def test_ws_get_services(ws):
    """get_services via WS returns service list."""
    result = await ws.send_command("get_services")
    assert result["success"] is True
    services = result["result"]
    assert isinstance(services, list)
    domains = [s["domain"] for s in services]
    assert "light" in domains
    assert "switch" in domains


# ── Persistent Notifications via WS ──────────────────────────

async def test_ws_persistent_notification_create(ws, rest):
    """Creating persistent_notification via WS call_service works."""
    result = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "title": "WS Test",
            "message": "Created via WebSocket",
            "notification_id": "ws_test_notif",
        },
    )
    assert result["success"] is True


async def test_ws_persistent_notification_dismiss(ws, rest):
    """Dismissing persistent_notification via WS works."""
    # Create first
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "title": "Dismiss Me",
            "message": "Will be dismissed",
            "notification_id": "ws_dismiss_notif",
        },
    )
    # Dismiss
    result = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": "ws_dismiss_notif"},
    )
    assert result["success"] is True


# ── WS Protocol Edge Cases ──────────────────────────────────

async def test_ws_unknown_command_returns_error(ws):
    """Unknown WS command type returns error."""
    result = await ws.send_command("nonexistent_command_xyz")
    assert result["success"] is False


async def test_ws_multiple_get_config(ws):
    """Multiple get_config calls return consistent data."""
    r1 = await ws.send_command("get_config")
    r2 = await ws.send_command("get_config")
    assert r1["result"]["location_name"] == r2["result"]["location_name"]
    assert r1["result"]["version"] == r2["result"]["version"]


async def test_ws_get_states_after_set(ws, rest):
    """get_states reflects recent state changes."""
    await rest.set_state("sensor.ws_states_sync", "sync_value_42")
    states = await ws.get_states()
    entity = next(s for s in states if s["entity_id"] == "sensor.ws_states_sync")
    assert entity["state"] == "sync_value_42"
