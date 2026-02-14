"""
CTS -- WebSocket State Event Delivery Depth Tests

Tests that WS subscribers receive state_changed events when entities
are modified via REST, verifies event structure, unsubscribe behavior,
and multiple subscriber isolation.
"""

import asyncio
import json
import uuid
import pytest
import websockets

pytestmark = pytest.mark.asyncio

WS_URL = "ws://localhost:8124/api/websocket"
BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def _connect_and_subscribe():
    """Connect, auth, subscribe to state_changed. Return (ws, sub_id)."""
    ws = await websockets.connect(WS_URL)
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_required"
    await ws.send(json.dumps({"type": "auth", "access_token": "test-token"}))
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_ok"
    # Subscribe
    await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))
    msg = json.loads(await ws.recv())
    assert msg["success"] is True
    return ws, 1


async def test_state_change_delivers_event(rest):
    """Setting state via REST delivers event to WS subscriber."""
    ws, sub_id = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_delivery_{tag}"
        await rest.set_state(eid, "test_value")

        # Receive events until we find ours (may get others)
        found = False
        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    event_data = msg.get("event", {}).get("data", {})
                    new_state = event_data.get("new_state", {})
                    if new_state.get("entity_id") == eid:
                        assert new_state["state"] == "test_value"
                        found = True
                        break
            except asyncio.TimeoutError:
                break
        assert found, f"Did not receive state_changed for {eid}"
    finally:
        await ws.close()


async def test_event_has_new_state_structure(rest):
    """State_changed event has new_state with entity_id, state, attributes."""
    ws, sub_id = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_struct_{tag}"
        await rest.set_state(eid, "hello", {"unit": "test"})

        found = False
        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    event_data = msg.get("event", {}).get("data", {})
                    new_state = event_data.get("new_state", {})
                    if new_state.get("entity_id") == eid:
                        assert "state" in new_state
                        assert "attributes" in new_state
                        assert new_state["state"] == "hello"
                        found = True
                        break
            except asyncio.TimeoutError:
                break
        assert found
    finally:
        await ws.close()


async def test_event_has_old_state(rest):
    """State_changed event includes old_state after update."""
    ws, _ = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_old_{tag}"
        await rest.set_state(eid, "first")
        # Drain the creation event
        for _ in range(10):
            try:
                await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                break

        # Now update
        await rest.set_state(eid, "second")
        found = False
        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    event_data = msg.get("event", {}).get("data", {})
                    new_state = event_data.get("new_state", {})
                    if new_state.get("entity_id") == eid and new_state.get("state") == "second":
                        old_state = event_data.get("old_state", {})
                        assert old_state.get("state") == "first"
                        found = True
                        break
            except asyncio.TimeoutError:
                break
        assert found
    finally:
        await ws.close()


async def test_event_subscription_id_matches(rest):
    """Event messages have id matching subscription id."""
    ws, sub_id = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_subid_{tag}"
        await rest.set_state(eid, "val")

        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    assert msg["id"] == sub_id
                    break
            except asyncio.TimeoutError:
                break
    finally:
        await ws.close()


async def test_unsubscribe_stops_events(rest):
    """After unsubscribe, no more events received for that subscription."""
    ws, sub_id = await _connect_and_subscribe()
    try:
        # Unsubscribe
        await ws.send(json.dumps({"id": 2, "type": "unsubscribe_events", "subscription": sub_id}))
        msg = json.loads(await ws.recv())
        assert msg["success"] is True

        # Set state — should not deliver event
        tag = uuid.uuid4().hex[:8]
        await rest.set_state(f"sensor.ws_unsub_{tag}", "val")

        # Wait briefly — should timeout with no event
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.5))
            # If we get something, it should NOT be an event with our sub_id
            if msg.get("type") == "event":
                assert msg["id"] != sub_id, "Received event after unsubscribe"
        except asyncio.TimeoutError:
            pass  # Expected — no events
    finally:
        await ws.close()


async def test_multiple_state_changes_deliver_multiple_events(rest):
    """Multiple state changes deliver multiple events."""
    ws, _ = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_multi_{tag}"
        for i in range(3):
            await rest.set_state(eid, str(i))
            await asyncio.sleep(0.05)

        event_count = 0
        for _ in range(30):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    ns = msg.get("event", {}).get("data", {}).get("new_state", {})
                    if ns.get("entity_id") == eid:
                        event_count += 1
            except asyncio.TimeoutError:
                break
        assert event_count >= 2, f"Expected >=2 events, got {event_count}"
    finally:
        await ws.close()


async def test_service_call_triggers_event(rest):
    """Service call via REST triggers state_changed event on WS."""
    ws, _ = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"light.ws_svc_{tag}"
        await rest.set_state(eid, "off")
        # Drain
        for _ in range(10):
            try:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                break

        await rest.call_service("light", "turn_on", {"entity_id": eid})

        found = False
        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    ns = msg.get("event", {}).get("data", {}).get("new_state", {})
                    if ns.get("entity_id") == eid and ns.get("state") == "on":
                        found = True
                        break
            except asyncio.TimeoutError:
                break
        assert found
    finally:
        await ws.close()


async def test_event_type_is_state_changed(rest):
    """Event wrapper has event_type: state_changed."""
    ws, _ = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.ws_etype_{tag}"
        await rest.set_state(eid, "x")

        for _ in range(20):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "event":
                    event = msg.get("event", {})
                    assert event.get("event_type") == "state_changed"
                    break
            except asyncio.TimeoutError:
                break
    finally:
        await ws.close()
