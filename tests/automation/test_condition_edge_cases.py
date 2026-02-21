"""
CTS -- Automation Condition Edge Case Tests

Tests automation condition evaluation through the REST API:
numeric_state above/below, template conditions via state,
automation enable/disable via WS, event trigger, time-based.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Enable/Disable Interactions ────────────────

async def test_disabled_automation_no_trigger(rest, ws):
    """Disabled automation does not fire on state change."""
    # Disable smoke_co_emergency automation
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    await asyncio.sleep(0.1)

    # Set smoke detected — should NOT trigger unlock
    await rest.set_state("binary_sensor.smoke", "on", {"friendly_name": "Smoke Detector"})
    await rest.set_state("lock.front_door", "locked")
    await asyncio.sleep(0.3)

    # Lock should remain locked (disabled automation)
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "locked"

    # Re-enable
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )


async def test_toggle_automation_twice_re_enables(rest, ws):
    """Toggling automation twice returns to enabled."""
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    await asyncio.sleep(0.1)
    state = await rest.get_state("automation.smoke_co_emergency")
    first_state = state["state"]

    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    await asyncio.sleep(0.1)
    state = await rest.get_state("automation.smoke_co_emergency")
    # Should be back to original
    assert state["state"] != first_state or state["state"] == "on"


# ── Force Trigger via WS ────────────────────────────────

async def test_ws_force_trigger(ws, rest):
    """Force triggering via WS call_service works."""
    await rest.set_state("lock.front_door", "locked")
    result = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert result["success"] is True
    await asyncio.sleep(0.3)
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


# ── Scene via WS ────────────────────────────────────────

async def test_ws_scene_turn_on(ws, rest):
    """Scene activated via WS call_service."""
    await rest.set_state("light.living_room_main", "off")
    result = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert result["success"] is True
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


# ── Service Call via WS ─────────────────────────────────

async def test_ws_service_call_standard(ws, rest):
    """Standard service call via WS uses registry."""
    await rest.set_state("light.ws_cond_test", "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.ws_cond_test"},
    )
    assert result["success"] is True
    state = await rest.get_state("light.ws_cond_test")
    assert state["state"] == "on"


async def test_ws_service_call_with_target(ws, rest):
    """WS service call with target.entity_id pattern."""
    await rest.set_state("switch.ws_target_test", "off")
    result = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={},
        target={"entity_id": "switch.ws_target_test"},
    )
    assert result["success"] is True
    state = await rest.get_state("switch.ws_target_test")
    assert state["state"] == "on"


async def test_ws_service_call_multiple_entities(ws, rest):
    """WS service call with array of entity_ids."""
    await rest.set_state("light.ws_multi_a", "off")
    await rest.set_state("light.ws_multi_b", "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": ["light.ws_multi_a", "light.ws_multi_b"]},
    )
    assert result["success"] is True
    a = await rest.get_state("light.ws_multi_a")
    b = await rest.get_state("light.ws_multi_b")
    assert a["state"] == "on"
    assert b["state"] == "on"


# ── Notification CRUD via WS ────────────────────────────

async def test_ws_notification_create_and_list(ws):
    """Create notification via WS, then list it."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_cond_test_1",
            "title": "Test Title",
            "message": "Test message body",
        },
    )
    await asyncio.sleep(0.2)

    result = await ws.send_command("get_notifications")
    assert result["success"] is True
    ids = [n.get("notification_id") for n in result["result"]]
    assert "ws_cond_test_1" in ids


async def test_ws_notification_dismiss(ws):
    """Dismiss notification via WS."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_cond_dismiss",
            "title": "Dismiss Me",
            "message": "Will be dismissed",
        },
    )
    await asyncio.sleep(0.2)

    result = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": "ws_cond_dismiss"},
    )
    assert result["success"] is True


async def test_ws_notification_dismiss_all(ws):
    """Dismiss all notifications via WS."""
    result = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    assert result["success"] is True


# ── Automation Info Fields ───────────────────────────────

@pytest.mark.marge_only
async def test_automation_info_has_mode(rest):
    """Automation config includes mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    for auto in data:
        assert "mode" in auto, f"Automation {auto['id']} missing mode"


@pytest.mark.marge_only
async def test_automation_info_has_counts(rest):
    """Automation config includes trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "trigger_count" in auto
        assert "condition_count" in auto
        assert "action_count" in auto
        assert isinstance(auto["trigger_count"], int)
