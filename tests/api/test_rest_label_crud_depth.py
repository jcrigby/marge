"""
CTS -- REST Label CRUD Depth Tests

Tests REST /api/labels endpoints: list, create, delete, label
entity assignment/unassignment, entity count, and label fields.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── List Labels ──────────────────────────────────────────

async def test_list_labels_returns_200(rest):
    """GET /api/labels returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_labels_returns_array(rest):
    """GET /api/labels returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    assert isinstance(resp.json(), list)


# ── Create Label ─────────────────────────────────────────

async def test_create_label_success(rest):
    """POST /api/labels creates label."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": f"lbl_{tag}", "name": f"Label {tag}", "color": "#00FF00"},
    )
    assert resp.status_code == 200


async def test_create_label_appears_in_list(rest):
    """Created label appears in GET /api/labels."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_crud_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": f"Test {tag}", "color": "#FF0000"},
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label_ids = [l["label_id"] for l in resp.json()]
    assert lid in label_ids


async def test_label_entry_has_fields(rest):
    """Label entry has label_id, name, color fields."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_flds_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Fields Test", "color": "#0000FF"},
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label = next(l for l in resp.json() if l["label_id"] == lid)
    assert label["name"] == "Fields Test"
    assert label["color"] == "#0000FF"


# ── Delete Label ─────────────────────────────────────────

async def test_delete_label_removes(rest):
    """DELETE /api/labels/<id> removes label from list."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Temp", "color": ""},
    )
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label_ids = [l["label_id"] for l in resp.json()]
    assert lid not in label_ids


# ── Entity Assignment ────────────────────────────────────

async def test_assign_label_to_entity(rest):
    """POST /api/labels/<lid>/entities/<eid> assigns label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_asgn_{tag}"
    eid = f"sensor.lbl_test_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Assign Test", "color": ""},
    )
    await rest.set_state(eid, "1")

    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_assigned_entity_in_label_listing(rest):
    """Assigned entity appears in label's entities array."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_elist_{tag}"
    eid = f"sensor.lbl_el_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "EList", "color": ""},
    )
    await rest.set_state(eid, "50")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label = next(l for l in resp.json() if l["label_id"] == lid)
    assert eid in label["entities"]


async def test_unassign_label_removes_entity(rest):
    """DELETE /api/labels/<lid>/entities/<eid> removes entity from label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_un_{tag}"
    eid = f"sensor.lbl_un_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Unassign", "color": ""},
    )
    await rest.set_state(eid, "v")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label = next(l for l in resp.json() if l["label_id"] == lid)
    assert eid not in label["entities"]


async def test_label_entity_count(rest):
    """Label listing includes correct entity_count."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_cnt_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
        json={"label_id": lid, "name": "Count", "color": ""},
    )
    for i in range(2):
        eid = f"sensor.lbl_cnt_{i}_{tag}"
        await rest.set_state(eid, str(i))
        await rest.client.post(
            f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
            headers=rest._headers(),
        )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    label = next(l for l in resp.json() if l["label_id"] == lid)
    assert label["entity_count"] == 2
