"""
CTS -- Notification REST Lifecycle Depth Tests

Tests persistent_notification service calls via REST and the
notification REST endpoints: create, list, dismiss, dismiss_all,
field presence, and re-create after dismiss cycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_notification(rest, notif_id, title="", message=""):
    """Create notification via service call."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": notif_id,
            "title": title,
            "message": message,
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def _list_notifications(rest):
    """List all active notifications."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Create + List ─────────────────────────────────────────

async def test_create_notification_appears_in_list(rest):
    """Created notification appears in notification list."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_create_{tag}"
    await _create_notification(rest, nid, "Test", "Hello")

    notifs = await _list_notifications(rest)
    ids = [n["notification_id"] for n in notifs]
    assert nid in ids


async def test_notification_has_title(rest):
    """Notification entry has title field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_title_{tag}"
    await _create_notification(rest, nid, "My Title", "body")

    notifs = await _list_notifications(rest)
    found = next(n for n in notifs if n["notification_id"] == nid)
    assert found["title"] == "My Title"


async def test_notification_has_message(rest):
    """Notification entry has message field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_msg_{tag}"
    await _create_notification(rest, nid, "Title", "My Message")

    notifs = await _list_notifications(rest)
    found = next(n for n in notifs if n["notification_id"] == nid)
    assert found["message"] == "My Message"


async def test_notification_has_created_at(rest):
    """Notification entry has created_at field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_ts_{tag}"
    await _create_notification(rest, nid, "T", "M")

    notifs = await _list_notifications(rest)
    found = next(n for n in notifs if n["notification_id"] == nid)
    assert "created_at" in found


async def test_notification_list_is_array(rest):
    """GET /api/notifications returns array."""
    notifs = await _list_notifications(rest)
    assert isinstance(notifs, list)


# ── Dismiss ───────────────────────────────────────────────

async def test_dismiss_notification(rest):
    """POST /api/notifications/:id/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_dismiss_{tag}"
    await _create_notification(rest, nid, "Dismiss Me", "Gone")

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    notifs = await _list_notifications(rest)
    ids = [n["notification_id"] for n in notifs]
    assert nid not in ids


async def test_dismiss_nonexistent_returns_404(rest):
    """Dismissing nonexistent notification returns 404."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/bogus_nrl_xyz/dismiss",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_dismiss_all_clears_all(rest):
    """POST /api/notifications/dismiss_all removes all notifications."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        await _create_notification(rest, f"nrl_da_{i}_{tag}", f"N{i}", f"M{i}")

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    notifs = await _list_notifications(rest)
    remaining = [n for n in notifs if f"nrl_da_" in n["notification_id"] and tag in n["notification_id"]]
    assert len(remaining) == 0


# ── Recreate After Dismiss ────────────────────────────────

async def test_recreate_after_dismiss(rest):
    """Notification can be recreated after dismissal."""
    tag = uuid.uuid4().hex[:8]
    nid = f"nrl_recreate_{tag}"

    await _create_notification(rest, nid, "V1", "First")
    await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )

    await _create_notification(rest, nid, "V2", "Second")
    notifs = await _list_notifications(rest)
    found = next(n for n in notifs if n["notification_id"] == nid)
    assert found["title"] == "V2"
    assert found["message"] == "Second"


# ── Multiple Notifications ────────────────────────────────

async def test_multiple_notifications_coexist(rest):
    """Multiple notifications with different IDs all appear."""
    tag = uuid.uuid4().hex[:8]
    nids = [f"nrl_multi_{i}_{tag}" for i in range(3)]
    for nid in nids:
        await _create_notification(rest, nid, nid, "msg")

    notifs = await _list_notifications(rest)
    listed_ids = {n["notification_id"] for n in notifs}
    for nid in nids:
        assert nid in listed_ids
