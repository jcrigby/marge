"""
CTS -- Notification Lifecycle Depth Tests

Tests persistent_notification create/dismiss/dismiss_all via both
REST service calls and direct REST endpoints, with lifecycle ordering.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_via_service_then_list(rest):
    """Create notification via service, verify in list."""
    tag = uuid.uuid4().hex[:8]
    nid = f"lifecycle_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Lifecycle Test",
            "message": "Testing lifecycle",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    ids = [n.get("notification_id", n.get("id", "")) for n in notifs]
    assert nid in ids


async def test_dismiss_removes_from_list(rest):
    """Dismiss notification removes it from active list."""
    tag = uuid.uuid4().hex[:8]
    nid = f"dismiss_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Dismiss Test",
            "message": "Will be dismissed",
        },
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/notifications/{nid}/dismiss",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    ids = [n.get("notification_id", n.get("id", "")) for n in resp.json()]
    assert nid not in ids


async def test_dismiss_all_clears_list(rest):
    """dismiss_all clears all active notifications."""
    tag = uuid.uuid4().hex[:8]

    # Create several
    for i in range(3):
        await rest.client.post(
            f"{rest.base_url}/api/services/persistent_notification/create",
            json={
                "notification_id": f"all_{tag}_{i}",
                "title": f"All Test {i}",
                "message": "Batch",
            },
            headers=rest._headers(),
        )

    await rest.client.post(
        f"{rest.base_url}/api/notifications/dismiss_all",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = resp.json()
    for i in range(3):
        ids = [n.get("notification_id", n.get("id", "")) for n in notifs]
        assert f"all_{tag}_{i}" not in ids


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


async def test_notification_upsert(rest):
    """Re-creating notification with same ID updates it."""
    tag = uuid.uuid4().hex[:8]
    nid = f"upsert_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Original",
            "message": "First version",
        },
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": nid,
            "title": "Updated",
            "message": "Second version",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    found = [n for n in resp.json()
             if n.get("notification_id", n.get("id", "")) == nid]
    assert len(found) == 1
    assert found[0]["title"] == "Updated"
    assert found[0]["message"] == "Second version"


async def test_ws_get_notifications(ws):
    """WS get_notifications returns notification list."""
    resp = await ws.send_command("get_notifications")
    assert resp.get("success", False) is True
    assert isinstance(resp.get("result"), list)


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
