"""
CTS -- Notification REST API Tests

Tests persistent notification create, list, dismiss,
and dismiss-all via the REST endpoints.
"""

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.marge_only
async def test_create_notification_via_service(rest):
    """POST persistent_notification.create adds a notification."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "rest_test_1",
        "title": "Test Title",
        "message": "Test message body",
    })

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    notifs = resp.json()
    ids = [n["notification_id"] for n in notifs]
    assert "rest_test_1" in ids


async def test_dismiss_nonexistent_returns_404(rest):
    """Dismissing a nonexistent notification returns 404."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/nonexistent_xyz/dismiss",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


@pytest.mark.marge_only
async def test_dismiss_via_service(rest):
    """persistent_notification.dismiss service removes by notification_id."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "rest_test_svc_dismiss",
        "title": "Svc Dismiss",
        "message": "Via service call",
    })

    await rest.call_service("persistent_notification", "dismiss", {
        "notification_id": "rest_test_svc_dismiss",
    })

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    ids = [n["notification_id"] for n in resp.json()]
    assert "rest_test_svc_dismiss" not in ids


@pytest.mark.marge_only
async def test_dismiss_all_via_service(rest):
    """persistent_notification.dismiss_all service clears notifications."""
    await rest.call_service("persistent_notification", "create", {
        "notification_id": "rest_test_svc_all",
        "title": "Clear Me",
        "message": "Via dismiss_all service",
    })

    await rest.call_service("persistent_notification", "dismiss_all", {})

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    ids = [n["notification_id"] for n in resp.json()]
    assert "rest_test_svc_all" not in ids
