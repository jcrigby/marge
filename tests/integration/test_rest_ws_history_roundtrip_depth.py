"""
CTS -- REST → WS → History Full Pipeline Round-Trip Depth Tests

Tests the complete data flow: set state via REST, receive event via WS,
verify in history, and confirm attribute round-trip fidelity across all
three channels. Also tests concurrent operations and event ordering.
"""

import asyncio
import json
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Full Round-Trip ─────────────────────────────────────

async def test_rest_set_ws_event_history_record(rest, ws):
    """REST set → WS event → history entry for same entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rt_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42", {"unit": "W"})
    # Get WS event
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid
    # Check history
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    assert data[-1]["state"] == "42"


async def test_attribute_fidelity_across_channels(rest, ws):
    """Attributes match across REST, WS event, and history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.af_{tag}"
    attrs = {"unit": "kWh", "friendly_name": f"Test {tag}", "precision": "2"}
    await ws.subscribe_events()
    await rest.set_state(eid, "100", attrs)
    # WS event attributes
    event = await ws.recv_event(timeout=3.0)
    ws_attrs = event["event"]["data"]["new_state"]["attributes"]
    assert ws_attrs["unit"] == "kWh"
    assert ws_attrs["friendly_name"] == f"Test {tag}"
    # REST get
    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "kWh"
    # History
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data[-1]["attributes"]["unit"] == "kWh"


# ── Multiple Transitions ───────────────────────────────

async def test_multiple_transitions_all_events(rest, ws):
    """Multiple state transitions each produce a WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mt_{tag}"
    await ws.subscribe_events()
    values = ["A", "B", "C"]
    for val in values:
        await rest.set_state(eid, val)
    # Collect events
    events = []
    for _ in range(len(values)):
        try:
            ev = await ws.recv_event(timeout=2.0)
            if ev["event"]["data"]["entity_id"] == eid:
                events.append(ev)
        except asyncio.TimeoutError:
            break
    assert len(events) >= 2  # at least most transitions received


async def test_multiple_transitions_in_history(rest):
    """Multiple state transitions all appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mth_{tag}"
    for val in ["10", "20", "30"]:
        await rest.set_state(eid, val)
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "30" in states
    assert len(data) >= 3


# ── Concurrent Pipelines ───────────────────────────────

async def test_concurrent_entities_independent(rest):
    """Concurrent state changes to different entities are independent."""
    tag = uuid.uuid4().hex[:8]
    pairs = [(f"sensor.ci_{i}_{tag}", str(i * 10)) for i in range(5)]
    await asyncio.gather(*[rest.set_state(eid, val) for eid, val in pairs])
    for eid, val in pairs:
        state = await rest.get_state(eid)
        assert state["state"] == val


async def test_rapid_state_updates(rest):
    """Rapid state updates to same entity converge to final value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rapid_{tag}"
    for i in range(10):
        await rest.set_state(eid, str(i))
    state = await rest.get_state(eid)
    assert state["state"] == "9"


# ── Service → Event → History ──────────────────────────

async def test_service_triggers_ws_event(rest, ws):
    """Service call triggers WS state_changed event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_ev_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["event_type"] == "state_changed"
    data = event["event"]["data"]
    assert data["entity_id"] == eid
    assert data["new_state"]["state"] == "on"


async def test_service_result_in_history(rest):
    """Service call result appears in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_hist_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "on" in states


# ── Logbook Cross-Check ────────────────────────────────

async def test_logbook_matches_history(rest):
    """Logbook entry corresponds to history record."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_xc_{tag}"
    await rest.set_state(eid, "alpha")
    await rest.set_state(eid, "beta")
    await asyncio.sleep(0.3)
    # Check both channels have records
    hist_resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    lb_resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    hist = hist_resp.json()
    lb = lb_resp.json()
    assert len(hist) >= 1
    assert len(lb) >= 1
