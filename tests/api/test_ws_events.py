"""
CTS -- WebSocket Event Subscription & Delivery Tests

Tests subscribe_events, state_changed event format, event filtering,
and WS command edge cases.
"""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


# ── State Changed Events ─────────────────────────────────

async def test_ws_state_changed_event_format(ws, rest):
    """State changes produce events with old/new state."""
    await rest.set_state("sensor.ws_event_fmt", "before")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_event_fmt", "after")

    event = await ws.recv_event(timeout=3.0)
    assert event["type"] == "event"
    assert event["id"] == sub_id
    data = event["event"]["data"]
    assert data["entity_id"] == "sensor.ws_event_fmt"
    assert data["new_state"]["state"] == "after"


async def test_ws_state_changed_has_old_state(ws, rest):
    """State changed events include old_state."""
    await rest.set_state("sensor.ws_old_state", "alpha")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_old_state", "beta")

    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["old_state"]["state"] == "alpha"
    assert data["new_state"]["state"] == "beta"


async def test_ws_state_changed_includes_attributes(ws, rest):
    """State changed events include entity attributes."""
    await rest.set_state("sensor.ws_attrs_test", "42", {"unit": "C"})
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_attrs_test", "43", {"unit": "C"})

    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert new_state["attributes"]["unit"] == "C"


# ── Get States via WS ────────────────────────────────────

async def test_ws_get_states_returns_list(ws, rest):
    """get_states WS command returns entity list."""
    await rest.set_state("sensor.ws_states_test", "123")
    states = await ws.get_states()
    assert isinstance(states, list)
    assert len(states) > 0
    ids = [s["entity_id"] for s in states]
    assert "sensor.ws_states_test" in ids


async def test_ws_get_states_entity_format(ws, rest):
    """Entities from get_states have expected fields."""
    await rest.set_state("sensor.ws_fmt_check", "42")
    states = await ws.get_states()
    entity = next(s for s in states if s["entity_id"] == "sensor.ws_fmt_check")
    assert entity["state"] == "42"
    assert "attributes" in entity
    assert "last_changed" in entity


# ── Call Service via WS ───────────────────────────────────

async def test_ws_call_service(ws, rest):
    """call_service via WS changes entity state."""
    await rest.set_state("light.ws_svc_test", "off")

    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.ws_svc_test"},
    )
    assert result["success"] is True

    state = await rest.get_state("light.ws_svc_test")
    assert state["state"] == "on"
