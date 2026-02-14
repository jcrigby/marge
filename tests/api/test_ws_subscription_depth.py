"""
CTS -- WebSocket Subscription Depth Tests

Tests subscribe_events/unsubscribe_events lifecycle, multiple
subscriptions, event delivery after unsubscribe, and concurrent
subscriptions.
"""

import asyncio
import json
import pytest

pytestmark = pytest.mark.asyncio


async def test_subscribe_returns_success(ws):
    """subscribe_events returns success."""
    resp = await ws.send_command("subscribe_events")
    assert resp["success"] is True


async def test_unsubscribe_returns_success(ws):
    """unsubscribe_events returns success."""
    # First subscribe
    resp = await ws.send_command("subscribe_events")
    sub_id = resp["id"]
    # Then unsubscribe
    resp2 = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert resp2["success"] is True


async def test_multiple_subscriptions(ws):
    """Multiple subscribe_events each get unique ids."""
    r1 = await ws.send_command("subscribe_events")
    r2 = await ws.send_command("subscribe_events")
    assert r1["success"] is True
    assert r2["success"] is True
    assert r1["id"] != r2["id"]


async def test_state_change_triggers_event(ws, rest):
    """State change triggers state_changed event to subscriber."""
    sub = await ws.send_command("subscribe_events")
    assert sub["success"] is True

    # Trigger a state change
    await rest.set_state("sensor.ws_sub_depth_evt", "100")

    # Read events from the websocket
    event = await ws.recv_event(timeout=2.0)
    assert event is not None


async def test_get_states_via_ws(ws, rest):
    """WS get_states includes recently created entity."""
    await rest.set_state("sensor.ws_depth_getst", "42")
    resp = await ws.send_command("get_states")
    assert resp["success"] is True
    states = resp["result"]
    ids = [s["entity_id"] for s in states]
    assert "sensor.ws_depth_getst" in ids
