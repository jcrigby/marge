"""
CTS -- WebSocket Notification Pipeline Depth Tests

Tests the WS persistent_notification lifecycle: create via call_service,
list via get_notifications, dismiss individual, dismiss_all.
Also tests WS fire_event, get_services, and get_config commands.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── WS Create Notification ───────────────────────────────

async def test_ws_create_notification(ws):
    """WS call_service persistent_notification.create succeeds."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command("call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": f"test_{tag}",
            "title": f"Test {tag}",
            "message": f"Message {tag}",
        },
    )
    assert resp["success"] is True


async def test_ws_created_notification_in_list(ws):
    """Created notification appears in get_notifications."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_{tag}"
    await ws.send_command("call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": f"Title {tag}",
            "message": f"Msg {tag}",
        },
    )
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    notifs = resp.get("result", [])
    nids = [n.get("notification_id") for n in notifs]
    assert nid in nids


async def test_ws_notification_has_title_and_message(ws):
    """Created notification has correct title and message."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_tm_{tag}"
    await ws.send_command("call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": f"Hello {tag}",
            "message": f"World {tag}",
        },
    )
    resp = await ws.send_command("get_notifications")
    notifs = resp.get("result", [])
    notif = next((n for n in notifs if n.get("notification_id") == nid), None)
    assert notif is not None
    assert notif["title"] == f"Hello {tag}"
    assert notif["message"] == f"World {tag}"


# ── WS Dismiss Notification ──────────────────────────────

async def test_ws_dismiss_notification(ws):
    """WS persistent_notification/dismiss removes one notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_dis_{tag}"
    await ws.send_command("call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Dismiss Me",
            "message": "Please",
        },
    )
    resp = await ws.send_command("persistent_notification/dismiss",
        notification_id=nid,
    )
    assert resp["success"] is True

    # Verify it's gone
    resp = await ws.send_command("get_notifications")
    notifs = resp.get("result", [])
    nids = [n.get("notification_id") for n in notifs]
    assert nid not in nids


# ── WS Dismiss via Service ───────────────────────────────

async def test_ws_dismiss_service(ws):
    """WS call_service persistent_notification.dismiss works."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_svc_dis_{tag}"
    await ws.send_command("call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "SvcDismiss",
            "message": "Test",
        },
    )
    await ws.send_command("call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": nid},
    )
    resp = await ws.send_command("get_notifications")
    notifs = resp.get("result", [])
    nids = [n.get("notification_id") for n in notifs]
    assert nid not in nids


# ── WS fire_event ─────────────────────────────────────────

async def test_ws_fire_event(ws):
    """WS fire_event succeeds."""
    resp = await ws.send_command("fire_event",
        event_type="test_event",
        event_data={"key": "value"},
    )
    assert resp["success"] is True


# ── WS get_services ───────────────────────────────────────

async def test_ws_get_services(ws):
    """WS get_services returns domain list."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    result = resp.get("result")
    assert result is not None


async def test_ws_get_services_has_domains(ws):
    """WS get_services includes standard domains."""
    resp = await ws.send_command("get_services")
    result = resp.get("result", {})
    # Result should contain domain keys
    text = str(result)
    assert "light" in text


# ── WS get_config ─────────────────────────────────────────

async def test_ws_get_config(ws):
    """WS get_config returns system configuration."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    result = resp.get("result", {})
    assert result.get("location_name") == "Marge Demo Home"


async def test_ws_get_config_has_coordinates(ws):
    """WS get_config includes latitude and longitude."""
    resp = await ws.send_command("get_config")
    result = resp.get("result", {})
    assert "latitude" in result
    assert "longitude" in result
    assert abs(result["latitude"] - 40.3916) < 0.01


async def test_ws_get_config_has_timezone(ws):
    """WS get_config includes time_zone."""
    resp = await ws.send_command("get_config")
    result = resp.get("result", {})
    assert result.get("time_zone") == "America/Denver"


# ── WS ping/pong ─────────────────────────────────────────

async def test_ws_ping_pong(ws):
    """WS ping returns true (pong received)."""
    result = await ws.ping()
    assert result is True
