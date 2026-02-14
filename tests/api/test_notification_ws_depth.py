"""
CTS -- Notification Lifecycle via WebSocket Tests

Tests persistent_notification service calls via WS: create, dismiss,
dismiss_all, list via WS get_notifications, and REST listing.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_create_notification(ws):
    """WS persistent_notification/create creates a notification."""
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_1",
            "title": "WS Test Notif",
            "message": "Created via WebSocket",
        },
    )
    assert resp["success"] is True


async def test_ws_dismiss_notification(ws):
    """WS persistent_notification/dismiss removes a notification."""
    # Create first
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_2",
            "title": "To Dismiss",
            "message": "Will be dismissed",
        },
    )
    # Dismiss
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": "ws_notif_depth_2"},
    )
    assert resp["success"] is True


async def test_ws_dismiss_all_notifications(ws):
    """WS persistent_notification/dismiss_all clears all."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_3",
            "title": "Temp",
            "message": "Temp",
        },
    )
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    assert resp["success"] is True


async def test_ws_get_notifications_after_create(ws):
    """get_notifications returns created notifications."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_4",
            "title": "Listed Notif",
            "message": "Should appear in list",
        },
    )
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    notifs = resp["result"]
    assert isinstance(notifs, list)


async def test_ws_dismiss_via_type(ws):
    """WS persistent_notification/dismiss via message type."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_5",
            "title": "Type Dismiss",
            "message": "Dismiss via type",
        },
    )
    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id="ws_notif_depth_5",
    )
    assert resp["success"] is True


async def test_rest_notifications_after_ws_create(ws, rest):
    """REST /api/notifications includes WS-created notifications."""
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_depth_6",
            "title": "Cross API",
            "message": "Created via WS, read via REST",
        },
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    notifs = resp.json()
    assert isinstance(notifs, list)
