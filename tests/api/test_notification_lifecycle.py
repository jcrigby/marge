"""
CTS -- Notification Lifecycle Tests

Tests persistent notification CRUD through both REST and WS APIs:
create, list, dismiss, dismiss_all, fields validation.
"""

import asyncio
import uuid

import pytest

pytestmark = pytest.mark.asyncio


# ── REST Notification Operations ─────────────────────────

@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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


@pytest.mark.marge_only
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

@pytest.mark.marge_only
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


# ── Merged from test_notification_lifecycle_depth.py ─────


@pytest.mark.marge_only
async def test_notification_has_created_at(rest):
    """Notification entry has created_at timestamp."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ts_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Timestamp",
            "message": "Has timestamp",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    found = [n for n in resp.json()
             if n.get("notification_id", n.get("id", "")) == nid]
    if len(found) > 0:
        assert "created_at" in found[0]
        assert "T" in found[0]["created_at"]


@pytest.mark.marge_only
async def test_ws_create_notification(ws, rest):
    """WS persistent_notification/create creates notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ws_create_{tag}"

    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "WS Created",
            "message": "Via WebSocket",
        },
    )
    assert resp.get("success", False) is True

    list_resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    ids = [n.get("notification_id", n.get("id", "")) for n in list_resp.json()]
    assert nid in ids


@pytest.mark.marge_only
async def test_notification_count_changes(rest):
    """Notification count increases after create, decreases after dismiss."""
    # Get initial count
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    count1 = len(resp1.json())

    tag = uuid.uuid4().hex[:8]
    nid = f"count_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Count",
            "message": "Counting",
        },
        headers=rest._headers(),
    )

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    count2 = len(resp2.json())
    assert count2 >= count1 + 1

    await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        json={},
        headers=rest._headers(),
    )

    resp3 = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    count3 = len(resp3.json())
    assert count3 < count2
