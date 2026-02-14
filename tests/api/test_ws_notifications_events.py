"""
CTS -- WebSocket Notifications and Fire Event Tests

Tests persistent_notification CRUD via WS call_service, notification
listing via get_notifications, dismiss operations, and fire_event.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Persistent Notification CRUD ──────────────────────────

async def test_create_notification(ws):
    """WS call_service persistent_notification.create succeeds."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": f"test_{tag}",
            "title": "Test Title",
            "message": "Test body message",
        },
    )
    assert resp.get("success", False) is True


async def test_get_notifications(ws):
    """WS get_notifications returns list."""
    resp = await ws.send_command("get_notifications")
    assert resp.get("success", False) is True
    result = resp.get("result", [])
    assert isinstance(result, list)


async def test_create_and_list_notification(ws):
    """Created notification appears in get_notifications."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"list_{tag}"

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "Listed",
            "message": "Should appear in list",
        },
    )

    # List
    resp = await ws.send_command("get_notifications")
    result = resp.get("result", [])
    ids = [n["notification_id"] for n in result]
    assert notif_id in ids


async def test_notification_fields(ws):
    """Created notification has title, message, created_at."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"fields_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "My Title",
            "message": "My Message",
        },
    )

    resp = await ws.send_command("get_notifications")
    result = resp.get("result", [])
    found = [n for n in result if n["notification_id"] == notif_id]
    assert len(found) == 1
    assert found[0]["title"] == "My Title"
    assert found[0]["message"] == "My Message"
    assert "created_at" in found[0]


async def test_dismiss_notification(ws):
    """WS persistent_notification/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"dismiss_{tag}"

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "To Dismiss",
            "message": "Going away",
        },
    )

    # Dismiss
    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=notif_id,
    )
    assert resp.get("success", False) is True

    # Verify gone from list
    list_resp = await ws.send_command("get_notifications")
    ids = [n["notification_id"] for n in list_resp.get("result", [])]
    assert notif_id not in ids


async def test_dismiss_all_notifications(ws):
    """WS call_service persistent_notification.dismiss_all clears all."""
    tag = uuid.uuid4().hex[:8]

    # Create two notifications
    for i in range(2):
        await ws.send_command(
            "call_service",
            domain="persistent_notification",
            service="create",
            service_data={
                "notification_id": f"all_{tag}_{i}",
                "title": f"Bulk {i}",
                "message": "Dismiss all test",
            },
        )

    # Dismiss all
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    assert resp.get("success", False) is True

    # Verify all dismissed
    list_resp = await ws.send_command("get_notifications")
    result = list_resp.get("result", [])
    remaining = [n for n in result if n["notification_id"].startswith(f"all_{tag}")]
    assert len(remaining) == 0


async def test_overwrite_notification(ws):
    """Creating notification with same ID overwrites it."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"overwrite_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "V1",
            "message": "First",
        },
    )

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "V2",
            "message": "Second",
        },
    )

    resp = await ws.send_command("get_notifications")
    found = [n for n in resp.get("result", []) if n["notification_id"] == notif_id]
    assert len(found) == 1
    assert found[0]["title"] == "V2"
    assert found[0]["message"] == "Second"


# ── Fire Event ────────────────────────────────────────────

async def test_fire_event_via_ws(ws):
    """WS fire_event returns success."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "fire_event",
        event_type=f"test_event_{tag}",
        event_data={"key": "value"},
    )
    assert resp.get("success", False) is True


async def test_fire_event_custom_type(ws):
    """WS fire_event with custom event type succeeds."""
    resp = await ws.send_command(
        "fire_event",
        event_type="custom_integration_event",
        event_data={"source": "test"},
    )
    assert resp.get("success", False) is True


async def test_fire_event_no_data(ws):
    """WS fire_event without event_data succeeds."""
    resp = await ws.send_command(
        "fire_event",
        event_type="minimal_event",
    )
    assert resp.get("success", False) is True
