"""
CTS -- REST Notification Listing Depth Tests

Tests GET /api/notifications endpoint and dismiss operations
via REST endpoints.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── List Notifications ──────────────────────────────────

async def test_notifications_returns_200(rest):
    """GET /api/notifications returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_notifications_returns_array(rest):
    """GET /api/notifications returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


# ── Create + List ───────────────────────────────────────

async def test_notification_created_via_service_appears(rest, ws):
    """Notification created via WS service appears in REST listing."""
    tag = uuid.uuid4().hex[:8]
    nid = f"notif_{tag}"
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": f"Test {tag}",
            "message": "Test message",
        },
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    nids = [n.get("notification_id", "") for n in notifs]
    assert nid in nids


# ── Dismiss ─────────────────────────────────────────────

async def test_dismiss_notification(rest, ws):
    """Dismissing notification removes it from listing."""
    tag = uuid.uuid4().hex[:8]
    nid = f"dismiss_{tag}"
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Dismiss Me",
            "message": "Temp",
        },
    )

    await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    nids = [n.get("notification_id", "") for n in resp.json()]
    assert nid not in nids


async def test_dismiss_all_notifications(rest, ws):
    """Dismiss all clears notification list."""
    tag = uuid.uuid4().hex[:8]
    for i in range(2):
        await ws.send_command(
            "call_service",
            domain="persistent_notification",
            service="create",
            service_data={
                "notification_id": f"dall_{i}_{tag}",
                "title": f"Temp {i}",
                "message": "Clear me",
            },
        )

    await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    remaining = [n for n in notifs if f"dall_" in n.get("notification_id", "") and tag in n.get("notification_id", "")]
    assert len(remaining) == 0
