"""
CTS -- Automation Control via WebSocket Depth Tests

Tests automation control through WS call_service: trigger, turn_on,
turn_off, toggle, and automation info/state verification.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_automation_trigger(ws, rest):
    """WS call_service automation/trigger fires automation."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp["success"] is True


async def test_ws_automation_turn_off(ws, rest):
    """WS automation/turn_off disables automation entity."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp["success"] is True

    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "off"


async def test_ws_automation_turn_on(ws, rest):
    """WS automation/turn_on re-enables automation entity."""
    # Disable first
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    # Re-enable
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp["success"] is True

    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "on"


async def test_ws_automation_toggle(ws, rest):
    """WS automation/toggle flips automation state."""
    # Ensure enabled first
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )

    state_before = await rest.get_state("automation.smoke_co_emergency")
    assert state_before["state"] == "on"

    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp["success"] is True

    state_after = await rest.get_state("automation.smoke_co_emergency")
    assert state_after["state"] == "off"

    # Toggle back
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    state_final = await rest.get_state("automation.smoke_co_emergency")
    assert state_final["state"] == "on"


async def test_ws_automation_trigger_returns_empty(ws):
    """WS automation trigger returns empty array result."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp["success"] is True
    assert resp["result"] == []


async def test_ws_scene_turn_on(ws, rest):
    """WS scene/turn_on activates scene."""
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert resp["success"] is True
    assert resp["result"] == []


async def test_ws_call_service_returns_changed(ws, rest):
    """WS call_service for standard domain returns changed states."""
    await rest.set_state("light.ws_depth_svc", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.ws_depth_svc", "brightness": 128},
    )
    assert resp["success"] is True
    changed = resp["result"]
    assert isinstance(changed, list)
    assert len(changed) > 0
    assert changed[0]["entity_id"] == "light.ws_depth_svc"
    assert changed[0]["state"] == "on"


async def test_ws_call_service_target_pattern(ws, rest):
    """WS call_service with target.entity_id pattern also works."""
    await rest.set_state("switch.ws_depth_target", "off")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        target={"entity_id": "switch.ws_depth_target"},
    )
    assert resp["success"] is True
    state = await rest.get_state("switch.ws_depth_target")
    assert state["state"] == "on"
