"""
CTS -- Service → State → Event Chain Depth Tests

Tests the complete chain: calling a service via REST triggers a state
change, which fires a WS event, which is recorded in history. Covers
multiple domains and service types through the full pipeline.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Light Service Chain ─────────────────────────────────

async def test_light_turn_on_chain(rest, ws):
    """light.turn_on → state on → WS event → history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.chain_{tag}"
    await rest.set_state(eid, "off")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "on"
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    states = [e["state"] for e in resp.json()]
    assert "on" in states


async def test_light_turn_off_chain(rest, ws):
    """light.turn_off → state off → WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.chain_off_{tag}"
    await rest.set_state(eid, "on")
    await ws.subscribe_events()
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "off"


# ── Lock Service Chain ──────────────────────────────────

async def test_lock_chain(rest, ws):
    """lock.lock → state locked → WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.chain_{tag}"
    await rest.set_state(eid, "unlocked")
    await ws.subscribe_events()
    await rest.call_service("lock", "lock", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "locked"


# ── Climate Service Chain ──────────────────────────────

async def test_climate_set_temperature_chain(rest, ws):
    """climate.set_temperature → temp attribute → WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.chain_{tag}"
    await rest.set_state(eid, "heat")
    await ws.subscribe_events()
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 72,
    })
    event = await ws.recv_event(timeout=3.0)
    attrs = event["event"]["data"]["new_state"]["attributes"]
    assert attrs["temperature"] == 72


# ── Toggle Service Chain ───────────────────────────────

async def test_toggle_chain(rest, ws):
    """toggle on→off → WS event with correct new_state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.chain_tog_{tag}"
    await rest.set_state(eid, "on")
    await ws.subscribe_events()
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "off"


# ── Cover Service Chain ────────────────────────────────

async def test_cover_open_chain(rest, ws):
    """cover.open_cover → state open → WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.chain_{tag}"
    await rest.set_state(eid, "closed")
    await ws.subscribe_events()
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "open"


# ── Multi-Service Sequence ─────────────────────────────

async def test_multi_service_sequence(rest):
    """Multiple services on same entity in sequence."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.chain_multi_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
    await rest.call_service("light", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Alarm Service Chain ────────────────────────────────

async def test_alarm_arm_chain(rest, ws):
    """alarm_control_panel.alarm_arm_home → armed_home → WS event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"alarm_control_panel.chain_{tag}"
    await rest.set_state(eid, "disarmed")
    await ws.subscribe_events()
    await rest.call_service("alarm_control_panel", "arm_home", {"entity_id": eid})
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["new_state"]["state"] == "armed_home"


# ── Concurrent Service Chains ──────────────────────────

async def test_concurrent_service_chains(rest):
    """Concurrent services on different entities are independent."""
    tag = uuid.uuid4().hex[:8]
    entities = [
        (f"light.cc_{i}_{tag}", "light", "turn_on")
        for i in range(5)
    ]
    for eid, _, _ in entities:
        await rest.set_state(eid, "off")
    await asyncio.gather(*[
        rest.call_service(domain, svc, {"entity_id": eid})
        for eid, domain, svc in entities
    ])
    for eid, _, _ in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on"
