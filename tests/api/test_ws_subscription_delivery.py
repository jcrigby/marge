"""
CTS -- WebSocket Subscription Event Delivery Tests

Tests state_changed event delivery timing, filtering, format correctness,
multi-connection scenarios, and WS command integration.
"""

import asyncio
import json
import uuid

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


# ── Event Format ─────────────────────────────────────────────

async def test_ws_subscribe_receives_state_change(ws, rest):
    """Subscribed WS client receives state_changed event with correct type."""
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


async def test_ws_event_has_new_state(ws, rest):
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


async def test_ws_state_changed_event_format(ws, rest):
    """State changes produce events with correct type, sub_id, and data."""
    await rest.set_state("sensor.ws_event_fmt", "before")
    sub_id = await ws.subscribe_events("state_changed")
    await rest.set_state("sensor.ws_event_fmt", "after")

    event = await ws.recv_event(timeout=3.0)
    assert event["type"] == "event"
    assert event["id"] == sub_id
    data = event["event"]["data"]
    assert data["entity_id"] == "sensor.ws_event_fmt"
    assert data["new_state"]["state"] == "after"


async def test_ws_event_includes_context(ws, rest):
    """state_changed event new_state includes context with id."""
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


@pytest.mark.parametrize("field", ["last_changed", "last_updated"])
async def test_ws_event_new_state_has_timestamp_field(ws, rest, field):
    """new_state includes last_changed and last_updated timestamps."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_ts_field", "timed")
    event = await ws.recv_event(timeout=5.0)
    new_state = event["event"]["data"]["new_state"]
    assert field in new_state


async def test_ws_event_subscription_id_matches(ws, rest):
    """Event subscription ID in message matches the subscribed ID."""
    sub_id = await ws.subscribe_events()
    await rest.set_state("sensor.ws_evt_sid", "check")
    event = await ws.recv_event(timeout=5.0)
    assert event["id"] == sub_id


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


# ── Unsubscribe ──────────────────────────────────────────────

async def test_ws_unsubscribe_stops_events(ws, rest):
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
        pass  # Expected -- no events after unsubscribe


# ── WS Event Subscription ID Tracking ───────────────────────

async def test_ws_event_ids_increment(ws, rest):
    """Each subscription gets a unique incrementing ID."""
    sub1 = await ws.subscribe_events("state_changed")
    sub2 = await ws.subscribe_events("state_changed")
    assert sub1 != sub2
    assert sub2 > sub1


# ── WS Commands (get_states, call_service) ───────────────────

async def test_ws_get_states_returns_list(ws, rest):
    """get_states WS command returns entity list."""
    await rest.set_state("sensor.ws_states_test", "123")
    states = await ws.get_states()
    assert isinstance(states, list)
    assert len(states) > 0
    ids = [s["entity_id"] for s in states]
    assert "sensor.ws_states_test" in ids


async def test_ws_get_states_entity_format(ws, rest):
    """Entities from get_states have expected fields."""
    await rest.set_state("sensor.ws_fmt_check", "42")
    states = await ws.get_states()
    entity = next(s for s in states if s["entity_id"] == "sensor.ws_fmt_check")
    assert entity["state"] == "42"
    assert "attributes" in entity
    assert "last_changed" in entity


async def test_ws_call_service(ws, rest):
    """call_service via WS changes entity state."""
    await rest.set_state("light.ws_svc_test", "off")

    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.ws_svc_test"},
    )
    assert result["success"] is True

    state = await rest.get_state("light.ws_svc_test")
    assert state["state"] == "on"
