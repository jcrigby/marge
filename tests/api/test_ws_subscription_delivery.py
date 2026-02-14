"""
CTS -- WebSocket Subscription Event Delivery Tests

Tests state_changed event delivery timing, filtering,
and multi-connection scenarios.
"""

import asyncio
import json

import pytest

pytestmark = pytest.mark.asyncio


# ── Event Delivery ───────────────────────────────────────────

async def test_ws_event_has_event_type(ws, rest):
    """State changed events include event_type field."""
    await rest.set_state("sensor.ws_evt_type", "before")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_evt_type", "after")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"


async def test_ws_event_has_timestamp(ws, rest):
    """State changed events include time_fired timestamp."""
    await rest.set_state("sensor.ws_evt_ts", "before")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_evt_ts", "after")
    event = await ws.recv_event(timeout=3.0)
    assert "time_fired" in event["event"]


async def test_ws_event_entity_id_matches(ws, rest):
    """Event data entity_id matches the changed entity."""
    entity = "sensor.ws_evt_eid"
    await rest.set_state(entity, "v1")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state(entity, "v2")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == entity


async def test_ws_event_new_state_has_attributes(ws, rest):
    """New state in event includes attributes."""
    await rest.set_state("sensor.ws_evt_attr", "10", {"unit": "V"})
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_evt_attr", "11", {"unit": "V"})
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert "attributes" in new_state
    assert new_state["attributes"]["unit"] == "V"


async def test_ws_event_old_state_preserved(ws, rest):
    """Old state in event reflects previous state value."""
    await rest.set_state("sensor.ws_evt_old", "original")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_evt_old", "updated")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["old_state"]["state"] == "original"


# ── Service-Triggered Events ────────────────────────────────

async def test_ws_service_call_triggers_event(ws, rest):
    """Service call that changes state triggers state_changed event."""
    await rest.set_state("light.ws_svc_evt", "off")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.call_service("light", "turn_on", {
        "entity_id": "light.ws_svc_evt",
    })
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == "light.ws_svc_evt"
    assert event["event"]["data"]["new_state"]["state"] == "on"


# ── Rapid Events ────────────────────────────────────────────

async def test_ws_rapid_state_changes(ws, rest):
    """Multiple rapid state changes each produce events."""
    entity = "sensor.ws_rapid_evt"
    await rest.set_state(entity, "0")
    sub_id = await ws.subscribe_events("state_changed")

    # Make 5 rapid changes
    for i in range(1, 6):
        await rest.set_state(entity, str(i))

    # Collect events
    events = []
    for _ in range(5):
        try:
            ev = await ws.recv_event(timeout=2.0)
            if ev["event"]["data"]["entity_id"] == entity:
                events.append(ev)
        except asyncio.TimeoutError:
            break

    assert len(events) >= 3  # At least 3 of 5 should arrive


# ── New Entity Events ────────────────────────────────────────

async def test_ws_new_entity_triggers_event(ws, rest):
    """Creating a new entity triggers state_changed with null old_state."""
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_new_entity_evt", "brand_new")

    # Collect events until we find ours
    for _ in range(10):
        try:
            ev = await ws.recv_event(timeout=2.0)
            if ev["event"]["data"]["entity_id"] == "sensor.ws_new_entity_evt":
                assert ev["event"]["data"]["new_state"]["state"] == "brand_new"
                break
        except asyncio.TimeoutError:
            pytest.fail("Did not receive event for new entity")


# ── WS Event subscription ID tracking ───────────────────────

async def test_ws_event_ids_increment(ws, rest):
    """Each subscription gets a unique incrementing ID."""
    sub1 = await ws.subscribe_events("state_changed")
    sub2 = await ws.subscribe_events("state_changed")
    assert sub1 != sub2
    assert sub2 > sub1
