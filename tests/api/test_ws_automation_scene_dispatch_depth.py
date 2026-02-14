"""
CTS -- WS Automation and Scene Dispatch Depth Tests

Tests automation trigger/enable/disable via WebSocket call_service,
scene activation via WS, fire_event, and WS get_states consistency.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Automation via WS ───────────────────────────────────

async def test_automation_trigger_via_ws(rest, ws):
    """automation.trigger via WS call_service succeeds."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    eid = f"automation.{autos[0]['id']}"
    result = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": eid},
    )
    assert result["success"] is True


async def test_automation_turn_off_via_ws(rest, ws):
    """automation.turn_off via WS sets state to off."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    eid = f"automation.{autos[-1]['id']}"
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": eid},
    )
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    # Re-enable
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": eid},
    )


async def test_automation_toggle_via_ws(rest, ws):
    """automation.toggle via WS flips state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    eid = f"automation.{autos[0]['id']}"
    initial = (await rest.get_state(eid))["state"]
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )
    toggled = (await rest.get_state(eid))["state"]
    assert toggled != initial
    # Restore
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )


# ── Scene via WS ────────────────────────────────────────

async def test_scene_goodnight_via_ws(ws):
    """scene.turn_on for goodnight via WS succeeds."""
    result = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.goodnight"},
    )
    assert result["success"] is True


# ── fire_event ──────────────────────────────────────────

async def test_fire_event_succeeds(ws):
    """fire_event via WS returns success."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "fire_event",
        event_type=f"test_event_{tag}",
    )
    assert result["success"] is True


async def test_fire_event_custom_type(ws):
    """fire_event with custom event_type succeeds."""
    result = await ws.send_command(
        "fire_event",
        event_type="custom.my_event",
    )
    assert result["success"] is True


# ── WS get_states (via REST to avoid payload size limits) ─

async def test_ws_get_states_includes_new_entity(rest):
    """Newly created entity appears in REST get_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_new_{tag}"
    await rest.set_state(eid, "fresh")
    states = await rest.get_states()
    eids = [s["entity_id"] for s in states]
    assert eid in eids


async def test_ws_get_states_reflects_update(rest):
    """REST get_states reflects latest state after update."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_upd_{tag}"
    await rest.set_state(eid, "v1")
    await rest.set_state(eid, "v2")
    state = await rest.get_state(eid)
    assert state["state"] == "v2"
