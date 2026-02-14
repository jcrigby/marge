"""
CTS -- WS Persistent Notification Dismiss Tests

Tests the WS persistent_notification/dismiss command directly
(not via call_service), and get_notifications query.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_notifications_success(ws):
    """get_notifications returns success with list result."""
    resp = await ws.send_command("get_notifications")
    assert resp["success"] is True
    assert isinstance(resp["result"], list)


async def test_create_notification_via_service_then_list(ws):
    """Create via call_service, verify via get_notifications."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ws_dismiss_{tag}"
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": f"Test {tag}",
            "message": "Test body",
        },
    )
    await asyncio.sleep(0.2)

    resp = await ws.send_command("get_notifications")
    ids = [n.get("notification_id") for n in resp["result"]]
    assert nid in ids


async def test_dismiss_via_ws_command(ws):
    """persistent_notification/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ws_cmd_dismiss_{tag}"

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Will Dismiss",
            "message": "Via WS command",
        },
    )
    await asyncio.sleep(0.2)

    # Dismiss via direct WS command
    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=nid,
    )
    assert resp["success"] is True

    # Verify gone
    await asyncio.sleep(0.1)
    list_resp = await ws.send_command("get_notifications")
    ids = [n.get("notification_id") for n in list_resp["result"]]
    assert nid not in ids


async def test_dismiss_nonexistent_notification(ws):
    """Dismissing nonexistent notification returns false."""
    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id="absolutely_nonexistent_999",
    )
    assert resp["success"] is False


async def test_notification_entry_has_fields(ws):
    """Notification entries have expected fields."""
    tag = uuid.uuid4().hex[:8]
    nid = f"ws_fields_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": f"Fields {tag}",
            "message": f"Body {tag}",
        },
    )
    await asyncio.sleep(0.2)

    resp = await ws.send_command("get_notifications")
    entry = next(
        (n for n in resp["result"] if n.get("notification_id") == nid),
        None,
    )
    assert entry is not None
    assert "title" in entry
    assert "message" in entry
    assert entry["title"] == f"Fields {tag}"


async def test_create_multiple_then_dismiss_one(ws):
    """Creating multiple, dismissing one leaves others."""
    tag = uuid.uuid4().hex[:8]
    nids = [f"ws_multi_{tag}_{i}" for i in range(3)]

    for nid in nids:
        await ws.send_command(
            "call_service",
            domain="persistent_notification",
            service="create",
            service_data={
                "notification_id": nid,
                "title": nid,
                "message": "test",
            },
        )
    await asyncio.sleep(0.2)

    # Dismiss only the middle one
    await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=nids[1],
    )
    await asyncio.sleep(0.1)

    resp = await ws.send_command("get_notifications")
    ids = [n.get("notification_id") for n in resp["result"]]
    assert nids[0] in ids
    assert nids[1] not in ids
    assert nids[2] in ids

    # Cleanup
    for nid in [nids[0], nids[2]]:
        await ws.send_command(
            "persistent_notification/dismiss",
            notification_id=nid,
        )
