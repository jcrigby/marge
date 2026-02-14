"""
CTS -- WebSocket State Event Delivery Depth Tests

Tests that state changes generate proper state_changed events
via WebSocket subscription, with correct event structure.
"""

import asyncio
import uuid
import json
import pytest
import websockets

pytestmark = pytest.mark.asyncio

WS_URL = "ws://localhost:8124/api/websocket"
TOKEN = "test-token"
BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def ws_connect_and_subscribe():
    """Connect, authenticate, and subscribe to state_changed events."""
    ws = await websockets.connect(WS_URL)

    # Auth required
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_required"

    # Authenticate
    await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_ok"

    # Subscribe to state_changed events
    await ws.send(json.dumps({
        "id": 1,
        "type": "subscribe_events",
        "event_type": "state_changed",
    }))
    msg = json.loads(await ws.recv())
    assert msg.get("success", False) is True

    return ws


async def test_state_change_generates_event(rest):
    """Setting state generates state_changed event on WS."""
    ws = await ws_connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_evt_{tag}"
        await rest.set_state(eid, "active")

        # Should receive event within timeout
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        assert msg["type"] == "event"
        event = msg["event"]
        assert event["event_type"] == "state_changed"
        assert "data" in event
    finally:
        await ws.close()


async def test_event_has_new_state(rest):
    """state_changed event contains new_state."""
    ws = await ws_connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_new_{tag}"
        await rest.set_state(eid, "val1")

        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        data = msg["event"]["data"]
        assert "new_state" in data
        assert data["new_state"]["entity_id"] == eid
        assert data["new_state"]["state"] == "val1"
    finally:
        await ws.close()


async def test_event_has_entity_id(rest):
    """state_changed event data has entity_id field."""
    ws = await ws_connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_eid_{tag}"
        await rest.set_state(eid, "check")

        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        data = msg["event"]["data"]
        assert data["entity_id"] == eid
    finally:
        await ws.close()


async def test_multiple_changes_generate_events(rest):
    """Multiple state changes generate multiple events."""
    ws = await ws_connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_multi_{tag}"
        events = []

        for i in range(3):
            await rest.set_state(eid, str(i))
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                events.append(msg)
            except asyncio.TimeoutError:
                break

        assert len(events) >= 2  # At least some events delivered
    finally:
        await ws.close()


async def test_unsubscribe_stops_events(rest):
    """After unsubscribe, no more events are delivered."""
    ws = await ws_connect_and_subscribe()
    try:
        # Unsubscribe
        await ws.send(json.dumps({
            "id": 2,
            "type": "unsubscribe_events",
            "subscription": 1,
        }))
        msg = json.loads(await ws.recv())
        assert msg.get("success", False) is True

        tag = uuid.uuid4().hex[:8]
        await rest.set_state(f"sensor.ws_unsub_{tag}", "val")

        # Should NOT receive an event
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.5))
            # If we get a message, it should not be a state_changed event for our entity
            if msg.get("type") == "event":
                assert msg["event"]["data"].get("entity_id") != f"sensor.ws_unsub_{tag}"
        except asyncio.TimeoutError:
            pass  # Expected — no event after unsubscribe
    finally:
        await ws.close()


async def test_event_has_old_state_on_update(rest):
    """state_changed event has old_state when entity was updated."""
    ws = await ws_connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_old_{tag}"
        await rest.set_state(eid, "initial")

        # Consume first event
        try:
            await asyncio.wait_for(ws.recv(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

        await rest.set_state(eid, "updated")
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
        data = msg["event"]["data"]
        assert "old_state" in data
        if data["old_state"] is not None:
            assert data["old_state"]["state"] == "initial"
    finally:
        await ws.close()
