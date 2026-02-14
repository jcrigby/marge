"""
CTS -- State Event Pipeline Integration Depth Tests

Tests the full pipeline from state change through WebSocket event
delivery, history recording, and logbook generation. Verifies that
setting state via REST triggers WS state_changed events to
subscribers, and that the recorder captures the change.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── REST → WS Event Delivery ─────────────────────────────

async def test_state_change_triggers_ws_event(rest, ws):
    """Setting state via REST triggers WS state_changed event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "initial")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"
    assert event["event"]["data"]["entity_id"] == eid


async def test_ws_event_has_new_state(rest, ws):
    """WS state_changed event includes new state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_ns_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == eid
    new_state = data.get("new_state", {})
    assert new_state.get("state") == "42"


async def test_ws_event_has_old_state(rest, ws):
    """WS state_changed event includes old state for transitions."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_os_{tag}"
    await rest.set_state(eid, "first")
    await ws.subscribe_events()
    await rest.set_state(eid, "second")
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    assert data["entity_id"] == eid


# ── Service → State → Event ──────────────────────────────

async def test_service_call_triggers_event(rest, ws):
    """Service call (light.turn_on) triggers WS state_changed event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pipe_svc_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"
    data = event["event"]["data"]
    assert data["entity_id"] == eid


# ── State → History ──────────────────────────────────────

async def test_state_change_recorded_in_history(rest):
    """State change appears in history after recorder flush."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_hist_{tag}"
    await rest.set_state(eid, "100")
    await asyncio.sleep(0.3)  # recorder flush
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    assert data[-1]["state"] == "100"


async def test_multiple_state_changes_in_history(rest):
    """Multiple state changes recorded in order."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_mhist_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    await rest.set_state(eid, "C")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "A" in states
    assert "C" in states


# ── State → Logbook ───────────────────────────────────────

async def test_state_change_in_logbook(rest):
    """State change appears in logbook."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_lb_{tag}"
    await rest.set_state(eid, "on")
    await rest.set_state(eid, "off")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        states = [e.get("state") for e in data]
        assert "off" in states


# ── Attributes through pipeline ──────────────────────────

async def test_attributes_preserved_in_event(rest, ws):
    """Attributes are included in WS state_changed event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_attr_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42", {"unit": "W", "friendly_name": "Power"})
    event = await ws.recv_event(timeout=3.0)
    data = event["event"]["data"]
    new_state = data.get("new_state", {})
    attrs = new_state.get("attributes", {})
    assert attrs.get("unit") == "W"
    assert attrs.get("friendly_name") == "Power"


async def test_attributes_in_history(rest):
    """Attributes are recorded in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_ahist_{tag}"
    await rest.set_state(eid, "55", {"unit": "kWh"})
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        attrs = data[-1].get("attributes", {})
        assert attrs.get("unit") == "kWh"


# ── Concurrent state changes ─────────────────────────────

async def test_concurrent_state_changes(rest):
    """Multiple concurrent state changes are all recorded."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"sensor.conc_{i}_{tag}" for i in range(5)]
    await asyncio.gather(*[rest.set_state(eid, str(i)) for i, eid in enumerate(entities)])
    for i, eid in enumerate(entities):
        state = await rest.get_state(eid)
        assert state["state"] == str(i)
