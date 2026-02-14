"""
CTS -- Notification REST API Depth Tests

Tests persistent_notification service calls via REST: create, list,
dismiss, dismiss_all, and notification lifecycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_notification_rest(rest):
    """Create notification via REST service call."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"rest_notif_{tag}",
            "title": "REST Test",
            "message": "Created via REST",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_notifications_rest(rest):
    """List notifications via REST."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    notifs = resp.json()
    assert isinstance(notifs, list)


async def test_create_then_list(rest):
    """Created notification appears in list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"rest_cl_{tag}",
            "title": "List Check",
            "message": "Should appear",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    ids = [n.get("notification_id", n.get("id", "")) for n in notifs]
    assert f"rest_cl_{tag}" in ids


async def test_dismiss_notification_rest(rest):
    """Dismiss notification via REST."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"rest_dis_{tag}",
            "title": "Dismiss Me",
            "message": "Will be dismissed",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/rest_dis_{tag}/dismiss",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_dismiss_all_rest(rest):
    """Dismiss all notifications via REST."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_notification_has_title(rest):
    """Notification entry has title field."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"rest_title_{tag}",
            "title": "Title Check",
            "message": "Body here",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    found = [n for n in notifs if n.get("notification_id", n.get("id", "")) == f"rest_title_{tag}"]
    if len(found) > 0:
        assert "title" in found[0]
        assert found[0]["title"] == "Title Check"


async def test_notification_has_message(rest):
    """Notification entry has message field."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"rest_msg_{tag}",
            "title": "Msg Check",
            "message": "Message body",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    found = [n for n in notifs if n.get("notification_id", n.get("id", "")) == f"rest_msg_{tag}"]
    if len(found) > 0:
        assert "message" in found[0]
        assert found[0]["message"] == "Message body"
