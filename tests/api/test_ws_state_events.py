"""
CTS -- WebSocket State Change Event Tests

Tests state_changed event delivery format, old_state tracking,
context propagation, and subscription filtering.
"""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_event_has_event_type(ws, rest):
    """State change event includes event_type field."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_type", "test_value")
    event = await ws.recv_event(timeout=5.0)
    assert event["type"] == "event"
    assert event["event"]["event_type"] == "state_changed"


async def test_ws_event_has_entity_id(ws, rest):
    """State change event data includes entity_id."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_eid", "42")
    event = await ws.recv_event(timeout=5.0)
    assert event["event"]["data"]["entity_id"] == "sensor.ws_evt_eid"


async def test_ws_event_has_new_state(ws, rest):
    """State change event includes new_state."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_new", "fresh")
    event = await ws.recv_event(timeout=5.0)
    data = event["event"]["data"]
    assert "new_state" in data
    assert data["new_state"]["state"] == "fresh"


async def test_ws_event_has_old_state(ws, rest):
    """State change event includes old_state after update."""
    await rest.set_state("sensor.ws_evt_old", "before")
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_old", "after")
    event = await ws.recv_event(timeout=5.0)
    data = event["event"]["data"]
    assert "old_state" in data
    if data["old_state"] is not None:
        assert data["old_state"]["state"] == "before"


async def test_ws_event_new_state_has_attributes(ws, rest):
    """new_state in event includes attributes."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_attrs", "50", {"unit": "lux"})
    event = await ws.recv_event(timeout=5.0)
    new_state = event["event"]["data"]["new_state"]
    assert "attributes" in new_state
    assert new_state["attributes"]["unit"] == "lux"


async def test_ws_event_has_context(ws, rest):
    """new_state includes context with id."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_ctx", "contextual")
    event = await ws.recv_event(timeout=5.0)
    new_state = event["event"]["data"]["new_state"]
    assert "context" in new_state
    assert "id" in new_state["context"]


async def test_ws_event_has_timestamps(ws, rest):
    """new_state includes last_changed and last_updated."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_ts", "timed")
    event = await ws.recv_event(timeout=5.0)
    new_state = event["event"]["data"]["new_state"]
    assert "last_changed" in new_state
    assert "last_updated" in new_state


async def test_ws_multiple_events_in_order(ws, rest):
    """Multiple state changes deliver events in order."""
    sub_id = await ws.subscribe_events()
    for i in range(3):
        await rest.set_state("sensor.ws_evt_order", str(i))
        await asyncio.sleep(0.05)

    states = []
    for _ in range(3):
        event = await ws.recv_event(timeout=5.0)
        states.append(event["event"]["data"]["new_state"]["state"])
    assert states == ["0", "1", "2"]


async def test_ws_event_subscription_id_matches(ws, rest):
    """Event subscription ID matches the subscribed ID."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_sid", "check")
    event = await ws.recv_event(timeout=5.0)
    assert event["id"] == sub_id


async def test_ws_service_triggers_event(ws, rest):
    """Service call triggers state_changed event."""
    await rest.set_state("light.ws_evt_svc", "off")
    sub_id = await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": "light.ws_evt_svc"})
    event = await ws.recv_event(timeout=5.0)
    assert event["event"]["data"]["entity_id"] == "light.ws_evt_svc"
    assert event["event"]["data"]["new_state"]["state"] == "on"
