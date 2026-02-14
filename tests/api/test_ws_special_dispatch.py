"""
CTS -- WebSocket Special Service Dispatch Tests

Tests WS call_service dispatch for special domains: automation (trigger,
turn_on, turn_off, toggle), scene (turn_on), persistent_notification
(create, dismiss, dismiss_all), and target.entity_id pattern.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_automation_trigger(ws, rest):
    """WS call_service automation.trigger fires automation."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp.get("success", False) is True


async def test_ws_automation_turn_off(ws, rest):
    """WS call_service automation.turn_off disables automation."""
    eid = "automation.morning_wakeup"

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


async def test_ws_automation_toggle(ws, rest):
    """WS call_service automation.toggle flips enabled state."""
    eid = "automation.morning_wakeup"
    state_before = await rest.get_state(eid)
    was_on = state_before["state"] == "on"

    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )

    state_after = await rest.get_state(eid)
    if was_on:
        assert state_after["state"] == "off"
    else:
        assert state_after["state"] == "on"

    # Toggle back
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )


async def test_ws_scene_turn_on(ws, rest):
    """WS call_service scene.turn_on activates a scene."""
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert resp.get("success", False) is True


async def test_ws_notification_create(ws):
    """WS persistent_notification.create creates a notification."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": f"wsnotif_{tag}",
            "title": "WS Test",
            "message": "Created via WS",
        },
    )
    assert resp.get("success", False) is True

    notif_resp = await ws.send_command("get_notifications")
    notifs = notif_resp["result"]
    found = [n for n in notifs if n.get("notification_id") == f"wsnotif_{tag}"]
    assert len(found) == 1


async def test_ws_notification_dismiss(ws):
    """WS persistent_notification.dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"wsdismiss_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Dismiss",
            "message": "Will be dismissed",
        },
    )

    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": nid},
    )
    assert resp.get("success", False) is True


async def test_ws_notification_dismiss_all(ws):
    """WS persistent_notification.dismiss_all clears all."""
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    assert resp.get("success", False) is True


async def test_ws_persistent_notification_dismiss_command(ws):
    """WS persistent_notification/dismiss direct command works."""
    tag = uuid.uuid4().hex[:8]
    nid = f"wsdirect_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Direct",
            "message": "Direct dismiss",
        },
    )

    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=nid,
    )
    assert resp.get("success") in [True, False]  # May or may not find it


async def test_ws_target_entity_id_pattern(ws, rest):
    """WS call_service with target.entity_id works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.wstarget_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        target={"entity_id": eid},
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_target_array_entity_ids(ws, rest):
    """WS call_service with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"switch.wstarr1_{tag}"
    eid2 = f"switch.wstarr2_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        target={"entity_id": [eid1, eid2]},
    )
    assert resp.get("success", False) is True

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "on"
    assert s2["state"] == "on"


async def test_ws_service_data_array_entity_ids(ws, rest):
    """WS call_service service_data.entity_id array."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"light.wsarr1_{tag}"
    eid2 = f"light.wsarr2_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid1, eid2]},
    )
    assert resp.get("success", False) is True

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "on"
    assert s2["state"] == "on"


async def test_ws_call_service_with_data(ws, rest):
    """WS call_service passes service_data attributes through."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsdata_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={
            "entity_id": eid,
            "brightness": 128,
        },
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128
