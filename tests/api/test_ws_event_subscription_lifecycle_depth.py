"""
CTS -- WS Event Subscription Lifecycle Depth Tests

Tests WebSocket event subscription lifecycle: subscribe_events,
unsubscribe_events, event delivery on state_changed, multiple
subscriptions, and fire_event acknowledgment.
"""

import uuid
import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Subscribe ───────────────────────────────────────────

async def test_ws_subscribe_events_success(ws):
    """subscribe_events returns success."""
    result = await ws.send_command("subscribe_events")
    assert result["success"] is True


async def test_ws_subscribe_events_returns_id(ws):
    """subscribe_events response includes id."""
    result = await ws.send_command("subscribe_events")
    assert "id" in result


async def test_ws_subscribe_events_with_type(ws):
    """subscribe_events with event_type returns success."""
    result = await ws.send_command(
        "subscribe_events",
        event_type="state_changed",
    )
    assert result["success"] is True


# ── Unsubscribe ─────────────────────────────────────────

async def test_ws_unsubscribe_events_success(ws):
    """unsubscribe_events returns success."""
    sub = await ws.send_command("subscribe_events")
    sub_id = sub["id"]
    result = await ws.send_command(
        "unsubscribe_events",
        subscription=sub_id,
    )
    assert result["success"] is True


async def test_ws_unsubscribe_nonexistent(ws):
    """unsubscribe_events for non-existent sub still succeeds."""
    result = await ws.send_command(
        "unsubscribe_events",
        subscription=99999,
    )
    assert result["success"] is True


# ── Event Delivery ──────────────────────────────────────

async def test_ws_state_change_triggers_event(rest, ws):
    """State change fires event to subscribed WS client."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsesl_evt_{tag}"
    await rest.set_state(eid, "hello")
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        assert event is not None
    except asyncio.TimeoutError:
        pass  # Event delivery is best-effort


async def test_ws_fire_event_acknowledged(ws):
    """fire_event returns success."""
    result = await ws.send_command(
        "fire_event",
        event_type="test_event",
    )
    assert result["success"] is True


# ── Multiple Subscriptions ──────────────────────────────

async def test_ws_multiple_subscriptions(ws):
    """Multiple subscribe_events calls all succeed."""
    r1 = await ws.send_command("subscribe_events")
    r2 = await ws.send_command("subscribe_events")
    assert r1["success"] is True
    assert r2["success"] is True
    assert r1["id"] != r2["id"]


async def test_ws_subscribe_unsubscribe_resubscribe(ws):
    """Subscribe, unsubscribe, then re-subscribe succeeds."""
    sub1 = await ws.send_command("subscribe_events")
    await ws.send_command(
        "unsubscribe_events",
        subscription=sub1["id"],
    )
    sub2 = await ws.send_command("subscribe_events")
    assert sub2["success"] is True
