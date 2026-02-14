"""
CTS -- WS Automation Control Depth Tests

Tests automation control via WebSocket: trigger, turn_on, turn_off,
toggle, and verify state changes through REST.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── WS Automation Services ───────────────────────────────

async def test_ws_automation_trigger(rest, ws):
    """WS automation.trigger succeeds."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.")
    )

    result = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": auto_eid},
    )
    assert result["success"] is True


async def test_ws_automation_turn_off_rest_verify(rest, ws):
    """WS automation.turn_off reflected in REST state."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.") and s["state"] == "on"
    )

    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": auto_eid},
    )

    state = await rest.get_state(auto_eid)
    assert state["state"] == "off"

    # Re-enable
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": auto_eid},
    )


async def test_ws_automation_turn_on(rest, ws):
    """WS automation.turn_on enables automation."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.")
    )

    # Disable first
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": auto_eid},
    )

    # Re-enable
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": auto_eid},
    )

    state = await rest.get_state(auto_eid)
    assert state["state"] == "on"


async def test_ws_automation_toggle_off(rest, ws):
    """WS automation.toggle from on to off."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.") and s["state"] == "on"
    )

    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": auto_eid},
    )

    state = await rest.get_state(auto_eid)
    assert state["state"] == "off"

    # Toggle back
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": auto_eid},
    )


# ── WS Scene Activation ─────────────────────────────────

async def test_ws_scene_turn_on(rest, ws):
    """WS scene.turn_on activates a scene."""
    # Get scene entities
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if not scenes:
        pytest.skip("No scenes loaded")

    scene_id = scenes[0]["id"]
    result = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": f"scene.{scene_id}"},
    )
    assert result["success"] is True
