"""
CTS -- WS Event Payload Detail Depth Tests

Tests the detailed structure of WebSocket state_changed events:
event_type field, data.entity_id, data.old_state/new_state objects,
time_fired, and nested entity fields within event payloads.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Event Structure ──────────────────────────────────────

async def test_event_has_event_type(rest, ws):
    """WS event has event_type field set to state_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_et_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"


async def test_event_data_has_entity_id(rest, ws):
    """WS event data contains entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_eid_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid


async def test_event_data_has_new_state_object(rest, ws):
    """WS event data.new_state is a full entity state object."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_ns_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42", {"unit": "W"})
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert new_state["entity_id"] == eid
    assert new_state["state"] == "42"
    assert "attributes" in new_state
    assert "last_changed" in new_state
    assert "last_updated" in new_state
    assert "context" in new_state


async def test_event_new_state_attributes(rest, ws):
    """WS event new_state contains the set attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_attr_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "55", {"unit": "kWh", "friendly_name": f"Power {tag}"})
    event = await ws.recv_event(timeout=3.0)
    attrs = event["event"]["data"]["new_state"]["attributes"]
    assert attrs["unit"] == "kWh"
    assert attrs["friendly_name"] == f"Power {tag}"


# ── Old State ────────────────────────────────────────────

async def test_event_old_state_null_for_new_entity(rest, ws):
    """First state set has old_state as null."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_null_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "first")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["old_state"] is None


async def test_event_old_state_populated_on_update(rest, ws):
    """Second state set has old_state with previous values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_old_{tag}"
    await rest.set_state(eid, "A", {"key": "val1"})
    await ws.subscribe_events()
    await rest.set_state(eid, "B", {"key": "val2"})
    event = await ws.recv_event(timeout=3.0)
    old = event["event"]["data"]["old_state"]
    assert old["state"] == "A"
    assert old["attributes"]["key"] == "val1"
    new = event["event"]["data"]["new_state"]
    assert new["state"] == "B"
    assert new["attributes"]["key"] == "val2"


# ── time_fired ───────────────────────────────────────────

async def test_event_time_fired_iso_format(rest, ws):
    """WS event time_fired is ISO 8601."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_tf_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    tf = event["event"]["time_fired"]
    assert isinstance(tf, str)
    assert "T" in tf
    assert "20" in tf  # year 20xx


# ── Service-Triggered Events ─────────────────────────────

async def test_service_produces_event_with_correct_state(rest, ws):
    """Service call triggers event with correct new state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.evd_svc_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid, "brightness": 200})
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert new_state["state"] == "on"
    assert new_state["attributes"]["brightness"] == 200


async def test_toggle_event_reflects_new_state(rest, ws):
    """Toggle service event shows the toggled state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.evd_tog_{tag}"
    await rest.set_state(eid, "on")
    await ws.subscribe_events()
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "off"


# ── Context in Events ────────────────────────────────────

async def test_event_new_state_context_has_id(rest, ws):
    """Event new_state.context.id is present and non-empty."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_ctx_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    ctx = event["event"]["data"]["new_state"]["context"]
    assert "id" in ctx
    assert len(ctx["id"]) > 0


async def test_event_context_unique_per_change(rest, ws):
    """Each state change gets a unique context id in the event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.evd_uq_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "A")
    ev1 = await ws.recv_event(timeout=3.0)
    await rest.set_state(eid, "B")
    ev2 = await ws.recv_event(timeout=3.0)
    ctx1 = ev1["event"]["data"]["new_state"]["context"]["id"]
    ctx2 = ev2["event"]["data"]["new_state"]["context"]["id"]
    assert ctx1 != ctx2
