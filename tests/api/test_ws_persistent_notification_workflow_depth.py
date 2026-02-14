"""
CTS -- WS Persistent Notification Workflow Depth Tests

Tests the full notification workflow via WebSocket: create via REST
service call, list via WS get_notifications, dismiss via WS command,
dismiss_all, and verify notification fields.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Create + WS List ────────────────────────────────────

async def test_ws_notifications_after_create(rest, ws):
    """Notification created via REST service appears in WS get_notifications."""
    tag = uuid.uuid4().hex[:8]
    await rest.call_service("persistent_notification", "create", {
        "title": f"Test {tag}",
        "message": f"Message {tag}",
        "notification_id": f"notif_{tag}",
    })

    result = await ws.send_command("get_notifications")
    assert result["success"] is True
    notifs = result["result"]
    found = [n for n in notifs if n.get("notification_id") == f"notif_{tag}"]
    assert len(found) >= 1


async def test_ws_notification_has_title(rest, ws):
    """WS notification entry has title field."""
    tag = uuid.uuid4().hex[:8]
    await rest.call_service("persistent_notification", "create", {
        "title": f"Title {tag}",
        "message": "msg",
        "notification_id": f"notif_t_{tag}",
    })

    result = await ws.send_command("get_notifications")
    found = [n for n in result["result"] if n.get("notification_id") == f"notif_t_{tag}"]
    assert found[0]["title"] == f"Title {tag}"


async def test_ws_notification_has_message(rest, ws):
    """WS notification entry has message field."""
    tag = uuid.uuid4().hex[:8]
    await rest.call_service("persistent_notification", "create", {
        "title": "t",
        "message": f"Body {tag}",
        "notification_id": f"notif_m_{tag}",
    })

    result = await ws.send_command("get_notifications")
    found = [n for n in result["result"] if n.get("notification_id") == f"notif_m_{tag}"]
    assert found[0]["message"] == f"Body {tag}"


# ── WS Dismiss ──────────────────────────────────────────

async def test_ws_dismiss_notification(rest, ws):
    """WS persistent_notification/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_wd_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "title": "Dismiss Me",
        "message": "...",
        "notification_id": nid,
    })

    result = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=nid,
    )
    assert result["success"] is True

    # Verify gone
    notifs = (await ws.send_command("get_notifications"))["result"]
    nids = [n.get("notification_id") for n in notifs]
    assert nid not in nids


async def test_ws_dismiss_nonexistent_notification(ws):
    """WS dismiss of nonexistent notification returns false."""
    result = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id="nonexistent_xyz_999",
    )
    assert result["success"] is False


# ── Multiple Notifications ──────────────────────────────

async def test_ws_multiple_notifications_listed(rest, ws):
    """Multiple notifications all appear in WS listing."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        await rest.call_service("persistent_notification", "create", {
            "title": f"Multi {i}",
            "message": f"msg {i}",
            "notification_id": f"notif_multi_{i}_{tag}",
        })

    result = await ws.send_command("get_notifications")
    nids = [n.get("notification_id") for n in result["result"]]
    for i in range(3):
        assert f"notif_multi_{i}_{tag}" in nids


async def test_ws_dismiss_one_preserves_others(rest, ws):
    """Dismissing one notification preserves the rest."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        await rest.call_service("persistent_notification", "create", {
            "title": f"Keep {i}",
            "message": f"msg {i}",
            "notification_id": f"notif_keep_{i}_{tag}",
        })

    # Dismiss the middle one
    await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=f"notif_keep_1_{tag}",
    )

    result = await ws.send_command("get_notifications")
    nids = [n.get("notification_id") for n in result["result"]]
    assert f"notif_keep_0_{tag}" in nids
    assert f"notif_keep_1_{tag}" not in nids
    assert f"notif_keep_2_{tag}" in nids
