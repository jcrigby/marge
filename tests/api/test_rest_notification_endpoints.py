"""
CTS -- REST Notification Endpoint Tests

Tests GET /api/notifications, POST /api/notifications/:id/dismiss,
and POST /api/notifications/dismiss_all REST endpoints.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def create_notification(rest, nid, title="Test", message="Body"):
    """Helper: create a notification via service call."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": nid,
        "title": title,
        "message": message,
    })
    await asyncio.sleep(0.2)


async def test_list_notifications_returns_200(rest):
    """GET /api/notifications returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_notifications_is_array(rest):
    """GET /api/notifications returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert isinstance(resp.json(), list)


async def test_created_notification_appears(rest):
    """Created notification appears in listing."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rest_notif_{tag}"
    await create_notification(rest, nid, f"Title {tag}", f"Message {tag}")

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    ids = [n.get("notification_id") for n in resp.json()]
    assert nid in ids


async def test_notification_has_title_and_message(rest):
    """Notification entry has title and message fields."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rest_fields_{tag}"
    await create_notification(rest, nid, f"Title {tag}", f"Msg {tag}")

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    entry = next(
        (n for n in resp.json() if n.get("notification_id") == nid),
        None,
    )
    assert entry is not None
    assert entry["title"] == f"Title {tag}"
    assert entry["message"] == f"Msg {tag}"


async def test_dismiss_notification_via_rest(rest):
    """POST /api/notifications/:id/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rest_dismiss_{tag}"
    await create_notification(rest, nid)

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
    ids = [n.get("notification_id") for n in list_resp.json()]
    assert nid not in ids


async def test_dismiss_nonexistent_notification(rest):
    """Dismissing nonexistent returns 200 (idempotent) or error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/nonexistent_999/dismiss",
        headers=rest._headers(),
    )
    # Should be 200 (idempotent) or 404
    assert resp.status_code in (200, 404)


async def test_dismiss_all_notifications(rest):
    """POST /api/notifications/dismiss_all clears all."""
    tag = uuid.uuid4().hex[:8]
    for i in range(3):
        await create_notification(rest, f"rest_all_{tag}_{i}", f"Title {i}")

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    await asyncio.sleep(0.1)
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert len(list_resp.json()) == 0


async def test_create_overwrite_notification(rest):
    """Creating with same ID overwrites title/message."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rest_over_{tag}"
    await create_notification(rest, nid, "Original", "Original body")
    await create_notification(rest, nid, "Updated", "Updated body")

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    entry = next(
        (n for n in resp.json() if n.get("notification_id") == nid),
        None,
    )
    assert entry is not None
    assert entry["title"] == "Updated"
    assert entry["message"] == "Updated body"


async def test_notification_has_created_at(rest):
    """Notification entry has created_at field."""
    tag = uuid.uuid4().hex[:8]
    nid = f"rest_ts_{tag}"
    await create_notification(rest, nid)

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    entry = next(
        (n for n in resp.json() if n.get("notification_id") == nid),
        None,
    )
    assert entry is not None
    assert "created_at" in entry
