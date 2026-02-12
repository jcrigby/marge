"""
CTS — WebSocket Subscribe Tests (~10 tests)

Tests the WebSocket API: connect, auth, subscribe_events, event delivery.
Validates SSS §5.1.2.
"""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_connect_and_auth(ws):
    """WebSocket connects and authenticates successfully."""
    # If we got the ws fixture without error, auth succeeded
    assert ws.ws is not None


async def test_ws_ping(ws):
    """WebSocket ping returns success."""
    result = await ws.ping()
    assert result is True


async def test_ws_get_states(ws):
    """get_states via WebSocket returns a list."""
    states = await ws.get_states()
    assert isinstance(states, list)


async def test_ws_subscribe_events(ws, rest):
    """subscribe_events returns success and events are delivered."""
    sub_id = await ws.subscribe_events("state_changed")

    # Trigger a state change
    await rest.set_state("test.ws_event_delivery", "triggered")

    # Should receive the event
    event = await ws.recv_event(timeout=3.0)
    assert event["type"] == "event"
    assert event["id"] == sub_id
    assert event["event"]["event_type"] == "state_changed"


async def test_ws_event_contains_entity_id(ws, rest):
    """State change events contain the correct entity_id."""
    await ws.subscribe_events("state_changed")
    await rest.set_state("test.ws_entity_check", "on")

    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == "test.ws_entity_check"


async def test_ws_event_has_old_and_new_state(ws, rest):
    """State change events include old_state and new_state."""
    await ws.subscribe_events("state_changed")

    # Set initial state
    await rest.set_state("test.ws_old_new", "first")
    # Drain initial event
    await ws.recv_event(timeout=3.0)

    # Change state
    await rest.set_state("test.ws_old_new", "second")
    event = await ws.recv_event(timeout=3.0)

    data = event["event"]["data"]
    assert data["new_state"]["state"] == "second"
    assert data["old_state"]["state"] == "first"


async def test_ws_multiple_subscriptions(ws, rest):
    """Multiple subscribe_events on same connection both receive events."""
    sub_id_1 = await ws.subscribe_events("state_changed")
    sub_id_2 = await ws.subscribe_events("state_changed")

    await rest.set_state("test.ws_multi_sub", "on")

    # Should get two events (one per subscription)
    events = []
    for _ in range(2):
        try:
            event = await ws.recv_event(timeout=3.0)
            events.append(event)
        except asyncio.TimeoutError:
            break

    assert len(events) == 2
    sub_ids = {e["id"] for e in events}
    assert sub_id_1 in sub_ids
    assert sub_id_2 in sub_ids
