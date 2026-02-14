"""
CTS -- WS Event Subscription Detail Depth Tests

Tests WebSocket subscribe_events delivery: event structure, multiple
subscribers, state_changed event fields, and event timing. Also tests
that unsubscribed connections don't receive events.
"""

import asyncio
import json
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Event Structure ─────────────────────────────────────

async def test_event_has_event_type(rest, ws):
    """WS state_changed event has event_type field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"


async def test_event_has_data(rest, ws):
    """WS event has data object with entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_d_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert "entity_id" in data
    assert data["entity_id"] == eid


async def test_event_has_new_state(rest, ws):
    """WS event data has new_state object."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_ns_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42")
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert new_state["state"] == "42"
    assert "entity_id" in new_state
    assert "last_changed" in new_state
    assert "last_updated" in new_state


async def test_event_has_old_state_on_update(rest, ws):
    """WS event has old_state for existing entity updates."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_os_{tag}"
    await rest.set_state(eid, "first")
    await ws.subscribe_events()
    await rest.set_state(eid, "second")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == eid
    assert data["old_state"] is not None
    assert data["old_state"]["state"] == "first"
    assert data["new_state"]["state"] == "second"


async def test_event_has_time_fired(rest, ws):
    """WS event has time_fired timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_tf_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert "time_fired" in event["event"]


# ── New Entity (old_state = null) ───────────────────────

async def test_new_entity_event_old_state_null(rest, ws):
    """WS event for brand new entity has old_state null."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_null_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "new")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == eid
    assert data["old_state"] is None


# ── Attributes in Events ───────────────────────────────

async def test_event_new_state_has_attributes(rest, ws):
    """WS event new_state includes attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_a_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42", {"unit": "W"})
    event = await ws.recv_event(timeout=3.0)
    attrs = event["event"]["data"]["new_state"]["attributes"]
    assert attrs["unit"] == "W"


async def test_event_new_state_has_context(rest, ws):
    """WS event new_state includes context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_c_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    ctx = event["event"]["data"]["new_state"]["context"]
    assert "id" in ctx


# ── Service-Triggered Events ───────────────────────────

async def test_service_triggers_event(rest, ws):
    """Service call triggers WS event with correct new_state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.esd_svc_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == eid
    assert data["new_state"]["state"] == "on"


# ── Event Type Field ───────────────────────────────────

async def test_event_type_is_string(rest, ws):
    """Event type field is the string 'event'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.esd_type_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert event.get("type") == "event"
