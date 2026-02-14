"""
CTS -- REST Notification Pipeline Depth Tests

Tests the REST API notification lifecycle: create via persistent_notification
service call, list via GET /api/notifications, dismiss individual,
dismiss all. Verifies roundtrip data integrity.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_notification(rest, nid, title, message):
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": title,
        "message": message,
    })


async def _list_notifications(rest):
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _dismiss(rest, nid):
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )
    return resp


async def _dismiss_all(rest):
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )
    return resp


# ── Create + List ─────────────────────────────────────────

async def test_create_notification_via_service(rest):
    """persistent_notification.create adds notification to list."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rn_{tag}"
    await _create_notification(rest, nid, f"Title {tag}", f"Msg {tag}")
    notifs = await _list_notifications(rest)
    nids = [n.get("notification_id") for n in notifs]
    assert nid in nids


async def test_notification_has_title(rest):
    """Created notification has correct title."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rn_t_{tag}"
    await _create_notification(rest, nid, f"MyTitle {tag}", "body")
    notifs = await _list_notifications(rest)
    notif = next(n for n in notifs if n.get("notification_id") == nid)
    assert notif["title"] == f"MyTitle {tag}"


async def test_notification_has_message(rest):
    """Created notification has correct message."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rn_m_{tag}"
    await _create_notification(rest, nid, "title", f"MyMessage {tag}")
    notifs = await _list_notifications(rest)
    notif = next(n for n in notifs if n.get("notification_id") == nid)
    assert notif["message"] == f"MyMessage {tag}"


# ── Dismiss Individual ────────────────────────────────────

async def test_dismiss_notification(rest):
    """POST /api/notifications/{id}/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rn_d_{tag}"
    await _create_notification(rest, nid, "DismissMe", "Please")
    resp = await _dismiss(rest, nid)
    assert resp.status_code == 200
    notifs = await _list_notifications(rest)
    nids = [n.get("notification_id") for n in notifs]
    assert nid not in nids


async def test_dismiss_nonexistent_returns_404(rest):
    """Dismissing non-existent notification returns 404."""
    resp = await _dismiss(rest, "nonexistent_xyz_99")
    assert resp.status_code == 404


# ── Dismiss All ───────────────────────────────────────────

async def test_dismiss_all_notifications(rest):
    """POST /api/notifications/dismiss_all clears all notifications."""
    tag = uuid.uuid4().hex[:8]
    await _create_notification(rest, f"rn_da1_{tag}", "One", "1")
    await _create_notification(rest, f"rn_da2_{tag}", "Two", "2")
    resp = await _dismiss_all(rest)
    assert resp.status_code == 200
    notifs = await _list_notifications(rest)
    # After dismiss_all, our tagged notifications should be gone
    tagged = [n for n in notifs if tag in n.get("notification_id", "")]
    assert len(tagged) == 0


# ── Full Lifecycle ────────────────────────────────────────

async def test_notification_full_lifecycle(rest):
    """Notification: create → list → verify → dismiss → confirm gone."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rn_life_{tag}"

    await _create_notification(rest, nid, "Lifecycle", "Test")

    notifs = await _list_notifications(rest)
    assert any(n.get("notification_id") == nid for n in notifs)

    resp = await _dismiss(rest, nid)
    assert resp.status_code == 200

    notifs = await _list_notifications(rest)
    assert not any(n.get("notification_id") == nid for n in notifs)
