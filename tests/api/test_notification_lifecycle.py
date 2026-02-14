"""
CTS -- Notification Lifecycle Tests

Tests persistent notification CRUD through both REST and WS APIs:
create, list, dismiss, dismiss_all, fields validation.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── REST Notification Operations ─────────────────────────

async def test_notification_create_via_service(rest):
    """Create notification via service call."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "notif_lc_1",
        "title": "Test Alert",
        "message": "Something happened",
    })
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    notifs = resp.json()
    ids = [n.get("notification_id") for n in notifs]
    assert "notif_lc_1" in ids


async def test_notification_has_fields(rest):
    """Notification includes title and message fields."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "notif_lc_fields",
        "title": "Field Test",
        "message": "Body text here",
    })
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    notif = next((n for n in notifs if n.get("notification_id") == "notif_lc_fields"), None)
    assert notif is not None
    assert notif["title"] == "Field Test"
    assert notif["message"] == "Body text here"


async def test_notification_dismiss_by_id(rest):
    """Dismiss specific notification by ID."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "notif_lc_dismiss",
        "title": "Dismiss Me",
        "message": "Will be dismissed",
    })
    await asyncio.sleep(0.2)

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/notif_lc_dismiss/dismiss",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    await asyncio.sleep(0.1)
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    ids = [n.get("notification_id") for n in notifs]
    assert "notif_lc_dismiss" not in ids


async def test_notification_dismiss_all(rest):
    """Dismiss all notifications."""
    # Create a few
    for i in range(3):
        await rest.call_service("persistent_notification", "create", {
            "notification_id": f"notif_lc_all_{i}",
            "title": f"Alert {i}",
            "message": f"Message {i}",
        })
    await asyncio.sleep(0.2)

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    await asyncio.sleep(0.1)
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


async def test_notification_overwrite(rest):
    """Creating notification with same ID overwrites it."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "notif_lc_overwrite",
        "title": "Original",
        "message": "First message",
    })
    await asyncio.sleep(0.2)

    await rest.call_service("persistent_notification", "create", {
        "notification_id": "notif_lc_overwrite",
        "title": "Updated",
        "message": "Second message",
    })
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    matching = [n for n in notifs if n.get("notification_id") == "notif_lc_overwrite"]
    assert len(matching) == 1
    assert matching[0]["title"] == "Updated"


# ── WS Notification Operations ──────────────────────────

async def test_ws_notification_roundtrip(ws):
    """Create notification via WS, list via WS, dismiss via WS."""
    # Clear all first
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    await asyncio.sleep(0.2)

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": "ws_notif_rt",
            "title": "WS Test",
            "message": "Created via WS",
        },
    )
    await asyncio.sleep(0.2)

    # List
    result = await ws.send_command("get_notifications")
    assert result["success"] is True
    ids = [n.get("notification_id") for n in result["result"]]
    assert "ws_notif_rt" in ids

    # Dismiss via WS persistent_notification/dismiss command
    result = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id="ws_notif_rt",
    )
    assert result["success"] is True

    # Verify gone
    await asyncio.sleep(0.1)
    result = await ws.send_command("get_notifications")
    ids = [n.get("notification_id") for n in result["result"]]
    assert "ws_notif_rt" not in ids
