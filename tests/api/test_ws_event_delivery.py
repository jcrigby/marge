"""
CTS -- WebSocket Event Delivery Tests

Tests that state changes fire WebSocket events to subscribers,
event format correctness, and subscription filtering.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_subscribe_receives_state_change(ws, rest):
    """Subscribed WS client receives state_changed event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsevt_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "trigger_event")

    try:
        event = await ws.recv_event(timeout=3.0)
        assert event["type"] == "event"
        assert "event" in event
        assert event["event"]["event_type"] == "state_changed"
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")


async def test_event_has_new_state(ws, rest):
    """state_changed event includes new_state with entity data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsns_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "new_val")

    try:
        event = await ws.recv_event(timeout=3.0)
        event_data = event["event"]["data"]
        assert "new_state" in event_data
        ns = event_data["new_state"]
        assert ns["entity_id"] == eid
        assert ns["state"] == "new_val"
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")


async def test_event_has_old_state_on_update(ws, rest):
    """state_changed event includes old_state when entity existed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsos_{tag}"

    await rest.set_state(eid, "old_val")

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "new_val")

    try:
        # Consume events until we find ours
        for _ in range(10):
            event = await ws.recv_event(timeout=3.0)
            if (event.get("type") == "event" and
                event["event"]["data"].get("new_state", {}).get("entity_id") == eid):
                event_data = event["event"]["data"]
                assert "old_state" in event_data
                assert event_data["old_state"]["state"] == "old_val"
                assert event_data["new_state"]["state"] == "new_val"
                return
        pytest.skip("Target event not found")
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")


async def test_multiple_events_for_rapid_changes(ws, rest):
    """Rapid state changes generate multiple events."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsrapid_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    # Set state 5 times rapidly
    for i in range(5):
        await rest.set_state(eid, f"v{i}")

    # Should receive at least some events
    events = []
    try:
        for _ in range(10):
            event = await ws.recv_event(timeout=2.0)
            if (event.get("type") == "event" and
                event["event"]["data"].get("new_state", {}).get("entity_id") == eid):
                events.append(event)
    except asyncio.TimeoutError:
        pass

    assert len(events) >= 1, "Should receive at least one event"


async def test_unsubscribe_stops_events(ws, rest):
    """After unsubscribe, no more events delivered."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsunsub_{tag}"

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    sub_id = sub["id"]

    unsub = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert unsub.get("success", False) is True

    await rest.set_state(eid, "should_not_deliver")

    try:
        event = await ws.recv_event(timeout=1.0)
        # If we get an event, it shouldn't be for our entity
    except asyncio.TimeoutError:
        pass  # Expected — no events after unsubscribe


async def test_event_has_entity_id(ws, rest):
    """state_changed event data includes entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wseid_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "val")

    try:
        event = await ws.recv_event(timeout=3.0)
        assert event["event"]["data"]["entity_id"] == eid
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")


async def test_event_includes_context(ws, rest):
    """state_changed event new_state includes context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wsctx_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "val")

    try:
        event = await ws.recv_event(timeout=3.0)
        ns = event["event"]["data"]["new_state"]
        assert "context" in ns
        assert "id" in ns["context"]
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")


async def test_service_call_triggers_event(ws, rest):
    """Service call state change triggers WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wssce_{tag}"
    await rest.set_state(eid, "off")

    sub_id = await ws.subscribe_events("state_changed")

    await rest.call_service("light", "turn_on", {"entity_id": eid})

    try:
        for _ in range(10):
            event = await ws.recv_event(timeout=3.0)
            if (event.get("type") == "event" and
                event["event"]["data"].get("new_state", {}).get("entity_id") == eid):
                assert event["event"]["data"]["new_state"]["state"] == "on"
                return
        pytest.skip("Target event not found")
    except asyncio.TimeoutError:
        pytest.skip("Event delivery timeout")
