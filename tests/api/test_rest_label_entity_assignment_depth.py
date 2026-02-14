"""
CTS -- REST Label Entity Assignment Depth Tests

Tests label entity assignment and unassignment via REST:
POST /api/labels/<lid>/entities/<eid> and DELETE.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Assign Entity to Label ──────────────────────────────

async def test_assign_entity_to_label(rest):
    """POST assigns entity to label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_asgn_{tag}"
    eid = f"sensor.lasgn_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"Label {tag}", "color": ""},
    )
    await rest.set_state(eid, "1")
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_assigned_entity_in_label_list(rest, ws):
    """Assigned entity appears in WS label listing."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_list_{tag}"
    eid = f"sensor.llist_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"List {tag}", "color": ""},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )

    result = await ws.send_command("config/label_registry/list")
    label = next(l for l in result["result"] if l["label_id"] == lid)
    assert eid in label["entities"]


# ── Unassign Entity from Label ──────────────────────────

async def test_unassign_entity_from_label(rest, ws):
    """DELETE removes entity from label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_unasgn_{tag}"
    eid = f"sensor.lunasgn_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"Unassign {tag}", "color": ""},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    del_resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200

    result = await ws.send_command("config/label_registry/list")
    label = next(l for l in result["result"] if l["label_id"] == lid)
    assert eid not in label["entities"]


# ── Delete Label Cleans Up ──────────────────────────────

async def test_delete_label_removes_from_registry(rest, ws):
    """Deleting label removes it from registry."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"Delete Me {tag}", "color": ""},
    )
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}",
        headers=rest._headers(),
    )

    result = await ws.send_command("config/label_registry/list")
    lids = [l["label_id"] for l in result["result"]]
    assert lid not in lids
