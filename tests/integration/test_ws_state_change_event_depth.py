"""
CTS -- WebSocket State Change Event Depth Tests

Tests the WebSocket subscribe_events → state_changed event pipeline in
detail: event payload structure, old_state/new_state fields, attribute
delivery, context propagation, multi-entity event ordering, and events
for entity creation vs updates.
"""

import asyncio
import json
import uuid
import pytest
import websockets

pytestmark = pytest.mark.asyncio

WS_URL = "ws://localhost:8124/api/websocket"
TOKEN = "test_token"


async def _connect_and_subscribe():
    """Connect WS, authenticate, and subscribe to state_changed events."""
    ws = await websockets.connect(WS_URL)
    auth_req = json.loads(await ws.recv())
    assert auth_req["type"] == "auth_required"
    await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
    auth_resp = json.loads(await ws.recv())
    assert auth_resp["type"] == "auth_ok"
    await ws.send(json.dumps({
        "id": 1,
        "type": "subscribe_events",
        "event_type": "state_changed",
    }))
    sub_resp = json.loads(await ws.recv())
    assert sub_resp.get("success", False) is True
    return ws


async def _drain_events(ws, timeout=0.5):
    """Drain all pending WS events within timeout."""
    events = []
    try:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            events.append(json.loads(raw))
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pass
    return events


async def _wait_for_entity_event(ws, entity_id, timeout=2.0):
    """Wait for a state_changed event for a specific entity."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("type") == "event":
                data = msg.get("event", {}).get("data", {})
                if data.get("entity_id") == entity_id:
                    return msg
        except (asyncio.TimeoutError, asyncio.CancelledError):
            break
    return None


# ── Event Payload Structure ──────────────────────────────

async def test_event_has_type_field(rest):
    """State change event has type=event."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_type_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "42")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["type"] == "event"
    finally:
        await ws.close()


async def test_event_has_event_type(rest):
    """Event contains event_type=state_changed."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_etype_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "99")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["event"]["event_type"] == "state_changed"
    finally:
        await ws.close()


async def test_event_data_has_entity_id(rest):
    """Event data contains the entity_id."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_eid_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "1")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["event"]["data"]["entity_id"] == eid
    finally:
        await ws.close()


# ── new_state / old_state Fields ─────────────────────────

async def test_new_entity_old_state_null(rest):
    """Creating new entity: old_state is null."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.old_null_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "first")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["event"]["data"]["old_state"] is None
    finally:
        await ws.close()


async def test_update_has_old_state(rest):
    """Updating entity: old_state contains previous state."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.old_prev_{tag}"
        await rest.set_state(eid, "before")
        await _drain_events(ws, 0.3)
        await rest.set_state(eid, "after")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        old = msg["event"]["data"]["old_state"]
        assert old is not None
        assert old["state"] == "before"
    finally:
        await ws.close()


async def test_new_state_matches_set(rest):
    """new_state reflects the value just set."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.new_match_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "value123")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["event"]["data"]["new_state"]["state"] == "value123"
    finally:
        await ws.close()


# ── Attributes in Events ────────────────────────────────

async def test_new_state_has_attributes(rest):
    """new_state includes attributes."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_attrs_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "42", {"unit": "W", "friendly_name": "Power"})
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        attrs = msg["event"]["data"]["new_state"]["attributes"]
        assert attrs["unit"] == "W"
        assert attrs["friendly_name"] == "Power"
    finally:
        await ws.close()


# ── Context in Events ───────────────────────────────────

async def test_new_state_has_context(rest):
    """new_state includes context with id."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_ctx_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "1")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        ctx = msg["event"]["data"]["new_state"]["context"]
        assert "id" in ctx
        assert len(ctx["id"]) > 0
    finally:
        await ws.close()


# ── Service Call Generates Event ─────────────────────────

async def test_service_call_triggers_event(rest):
    """Service call generates state_changed event."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"light.evt_svc_{tag}"
        await rest.set_state(eid, "off")
        await _drain_events(ws, 0.3)
        await rest.call_service("light", "turn_on", {"entity_id": eid})
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["event"]["data"]["new_state"]["state"] == "on"
    finally:
        await ws.close()


# ── Multi-Entity Event Delivery ──────────────────────────

async def test_events_for_multiple_entities(rest):
    """State changes to different entities all generate events."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eids = [f"sensor.evt_multi_{i}_{tag}" for i in range(3)]
        await _drain_events(ws, 0.2)
        for i, eid in enumerate(eids):
            await rest.set_state(eid, str(i * 10))

        events = await _drain_events(ws, 1.0)
        event_eids = set()
        for e in events:
            if e.get("type") == "event":
                event_eids.add(e["event"]["data"]["entity_id"])
        for eid in eids:
            assert eid in event_eids
    finally:
        await ws.close()


async def test_event_subscription_id(rest):
    """Events arrive with the subscription id."""
    ws = await _connect_and_subscribe()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.evt_subid_{tag}"
        await _drain_events(ws, 0.2)
        await rest.set_state(eid, "1")
        msg = await _wait_for_entity_event(ws, eid)
        assert msg is not None
        assert msg["id"] == 1  # subscription id from subscribe
    finally:
        await ws.close()
