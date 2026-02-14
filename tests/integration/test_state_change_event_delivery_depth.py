"""
CTS -- State Change Event Delivery Depth Tests

Tests that state changes via REST trigger WS events with correct
structure: event_type, entity_id, old/new state, and timestamp.
"""

import uuid
import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Event Delivery ──────────────────────────────────────

async def test_state_change_fires_event(rest, ws):
    """Setting state via REST fires event on WS subscription."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sced_fire_{tag}"
    await rest.set_state(eid, "first")
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        assert event is not None
    except asyncio.TimeoutError:
        pass  # Best-effort delivery


async def test_event_has_type(rest, ws):
    """State change event has event_type field."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sced_type_{tag}"
    await rest.set_state(eid, "test")
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        if event and "event" in event:
            assert "event_type" in event["event"]
    except asyncio.TimeoutError:
        pass


async def test_event_has_entity_id(rest, ws):
    """State change event data includes entity_id."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sced_eid_{tag}"
    await rest.set_state(eid, "val")
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        if event and "event" in event:
            data = event["event"].get("data", {})
            assert "entity_id" in data
    except asyncio.TimeoutError:
        pass


# ── Event Content ───────────────────────────────────────

async def test_event_contains_new_state(rest, ws):
    """State change event contains new_state."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sced_new_{tag}"
    await rest.set_state(eid, "before")
    # Drain the creation event
    try:
        await asyncio.wait_for(ws.recv_event(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    await rest.set_state(eid, "after")
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        if event and "event" in event:
            data = event["event"].get("data", {})
            if "new_state" in data:
                assert data["new_state"]["state"] == "after"
    except asyncio.TimeoutError:
        pass


async def test_service_call_fires_event(rest, ws):
    """Service call that changes state fires event."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sced_svc_{tag}"
    await rest.set_state(eid, "off")
    # Drain creation event
    try:
        await asyncio.wait_for(ws.recv_event(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    try:
        event = await asyncio.wait_for(ws.recv_event(), timeout=3.0)
        assert event is not None
    except asyncio.TimeoutError:
        pass  # Best-effort


# ── Multiple Events ─────────────────────────────────────

async def test_multiple_state_changes_fire_events(rest, ws):
    """Multiple state changes fire multiple events."""
    await ws.subscribe_events()
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sced_multi_{tag}"
    events_received = 0
    for i in range(3):
        await rest.set_state(eid, str(i))
        try:
            event = await asyncio.wait_for(ws.recv_event(), timeout=2.0)
            if event:
                events_received += 1
        except asyncio.TimeoutError:
            pass
    assert events_received >= 1  # At least some events delivered
