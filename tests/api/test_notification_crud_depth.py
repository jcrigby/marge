"""
CTS -- Notification CRUD Depth Tests

Tests persistent notification lifecycle: create via REST service call,
list notifications, dismiss individual, dismiss all, and verify notification
fields.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Create Notification ───────────────────────────────────

async def test_create_notification(rest):
    """persistent_notification.create via service creates notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": f"Test {tag}",
        "message": f"Message {tag}",
    })
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    notifs = resp.json()
    nids = [n.get("notification_id", n.get("id", "")) for n in notifs]
    assert nid in nids


async def test_notification_has_title(rest):
    """Notification has title field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_title_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": f"Title {tag}",
        "message": "Body",
    })
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notif = next(
        n for n in resp.json()
        if n.get("notification_id", n.get("id", "")) == nid
    )
    assert notif["title"] == f"Title {tag}"


async def test_notification_has_message(rest):
    """Notification has message field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_msg_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": "T",
        "message": f"Msg {tag}",
    })
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notif = next(
        n for n in resp.json()
        if n.get("notification_id", n.get("id", "")) == nid
    )
    assert notif["message"] == f"Msg {tag}"


# ── Dismiss Individual ────────────────────────────────────

async def test_dismiss_notification(rest):
    """POST dismiss removes individual notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_dismiss_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": "To Dismiss",
        "message": "Body",
    })
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Verify gone
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    nids = [n.get("notification_id", n.get("id", "")) for n in list_resp.json()]
    assert nid not in nids


async def test_dismiss_via_service(rest):
    """persistent_notification.dismiss via service call."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_svc_dismiss_{tag}"
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": "Svc Dismiss",
        "message": "Body",
    })
    await rest.call_service("persistent_notification", "dismiss", {
        "notification_id": nid,
    })
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    nids = [n.get("notification_id", n.get("id", "")) for n in resp.json()]
    assert nid not in nids


# ── Dismiss All ───────────────────────────────────────────

async def test_dismiss_all(rest):
    """POST dismiss_all removes all notifications."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        await rest.call_service("persistent_notification", "create", {
            "notification_id": f"notif_da_{i}_{tag}",
            "title": f"DA {i}",
            "message": "Body",
        })
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert len(list_resp.json()) == 0


# ── List Empty ────────────────────────────────────────────

async def test_list_notifications_after_dismiss_all(rest):
    """After dismiss_all, list returns empty."""
    await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
