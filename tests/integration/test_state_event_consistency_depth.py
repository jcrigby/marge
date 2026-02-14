"""
CTS -- State/Event Consistency Depth Tests

Tests that state changes and events are consistent: state change → WS
event has matching data, service call → state → event chain is atomic,
attribute changes propagate through events, and context is preserved.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── State → Event Consistency ─────────────────────────────

async def test_state_change_event_matches(rest, ws):
    """State change produces WS event with matching entity_id and state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid
    assert event["event"]["data"]["new_state"]["state"] == "42"


async def test_attribute_change_in_event(rest, ws):
    """Attribute changes appear in WS event new_state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_attr_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "10", {"unit": "W"})
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert new_state["attributes"]["unit"] == "W"


async def test_old_state_in_update_event(rest, ws):
    """Update to existing entity has old_state in event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_old_{tag}"
    await rest.set_state(eid, "first")
    await ws.subscribe_events()
    await rest.set_state(eid, "second")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["old_state"]["state"] == "first"
    assert data["new_state"]["state"] == "second"


# ── Service → State → Event Chain ─────────────────────────

async def test_service_state_event_chain(rest, ws):
    """Service call → state change → WS event chain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.sec_chain_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid
    assert event["event"]["data"]["new_state"]["state"] == "on"


async def test_toggle_state_event_consistency(rest, ws):
    """Toggle → correct state change event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.sec_tog_{tag}"
    await rest.set_state(eid, "on")
    await ws.subscribe_events()
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "off"


# ── Context Preservation ──────────────────────────────────

async def test_event_has_context_id(rest, ws):
    """WS event new_state has context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_ctx_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    ctx = event["event"]["data"]["new_state"]["context"]
    assert "id" in ctx
    assert len(ctx["id"]) > 0


async def test_event_has_entity_id_in_new_state(rest, ws):
    """WS event new_state contains entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_eid_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["entity_id"] == eid


# ── Timestamp Consistency ─────────────────────────────────

async def test_event_timestamps_present(rest, ws):
    """WS event new_state has last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_ts_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    new_state = event["event"]["data"]["new_state"]
    assert "last_changed" in new_state
    assert "last_updated" in new_state


async def test_event_time_fired_present(rest, ws):
    """WS event has time_fired."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sec_tf_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    event = await ws.recv_event(timeout=3.0)
    assert "time_fired" in event["event"]


# ── Multiple Events ───────────────────────────────────────

async def test_multiple_state_changes_multiple_events(rest, ws):
    """Multiple state changes produce multiple WS events."""
    tag = uuid.uuid4().hex[:8]
    await ws.subscribe_events()
    for i in range(3):
        eid = f"sensor.sec_multi_{i}_{tag}"
        await rest.set_state(eid, str(i))
    events = []
    for _ in range(3):
        try:
            event = await ws.recv_event(timeout=2.0)
            events.append(event)
        except asyncio.TimeoutError:
            break
    assert len(events) >= 3
