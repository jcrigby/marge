"""
CTS -- WS Service Call Patterns Depth Tests

Tests WebSocket call_service patterns: service_data vs target entity_id,
array entity_ids, persistent_notification via WS, and service response
format for different domains.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── WS call_service with service_data ─────────────────────

async def test_ws_call_service_light_on(rest, ws):
    """WS call_service light.turn_on with service_data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_svc_{tag}"
    await rest.set_state(eid, "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_call_service_light_off(rest, ws):
    """WS call_service light.turn_off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_off_{tag}"
    await rest.set_state(eid, "on")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_off",
        service_data={"entity_id": eid},
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ws_call_service_toggle(rest, ws):
    """WS call_service switch.toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_tog_{tag}"
    await rest.set_state(eid, "on")
    result = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── WS call_service with target ───────────────────────────

async def test_ws_call_service_with_target(rest, ws):
    """WS call_service using target.entity_id instead of service_data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_tgt_{tag}"
    await rest.set_state(eid, "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": eid},
    )
    assert result.get("success") is True
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── WS call_service with array entity_ids ─────────────────

async def test_ws_call_service_array_entities(rest, ws):
    """WS call_service with array of entity_ids."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.ws_arr_{i}_{tag}" for i in range(3)]
    for eid in entities:
        await rest.set_state(eid, "off")
    result = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": entities},
    )
    assert result.get("success") is True
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── WS Automation Services ────────────────────────────────

async def test_ws_automation_trigger(ws):
    """WS call_service automation.trigger succeeds."""
    result = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.morning_wakeup"},
    )
    assert result.get("success") is True


async def test_ws_automation_toggle(rest, ws):
    """WS call_service automation.toggle flips enabled state."""
    eid = "automation.morning_wakeup"
    # Get current state
    state = await rest.get_state(eid)
    original = state["state"]
    # Toggle
    result = await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )
    assert result.get("success") is True
    # Restore
    if original == "on":
        await ws.send_command(
            "call_service",
            domain="automation",
            service="turn_on",
            service_data={"entity_id": eid},
        )
    else:
        await ws.send_command(
            "call_service",
            domain="automation",
            service="turn_off",
            service_data={"entity_id": eid},
        )


# ── WS Scene Services ────────────────────────────────────

async def test_ws_scene_turn_on(ws):
    """WS call_service scene.turn_on activates scene."""
    result = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert result.get("success") is True


# ── WS Notification Services ─────────────────────────────

async def test_ws_persistent_notification_create(ws):
    """WS call_service persistent_notification.create."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": f"ws_notif_{tag}",
            "title": "Test",
            "message": "Test notification",
        },
    )
    assert result.get("success") is True


async def test_ws_get_notifications(ws):
    """WS get_notifications returns list."""
    result = await ws.send_command("get_notifications")
    assert result.get("success") is True
    assert isinstance(result.get("result"), list)


async def test_ws_persistent_notification_dismiss(ws):
    """WS persistent_notification/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ws_dismiss_{tag}"
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={"notification_id": nid, "title": "T", "message": "M"},
    )
    result = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=nid,
    )
    assert result.get("success") is True
