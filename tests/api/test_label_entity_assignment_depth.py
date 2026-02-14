"""
CTS -- Label Entity Assignment REST API Depth Tests

Tests the label REST API: create labels, list labels, assign/unassign
entities, verify entity_count, search by label, label color, upsert
(update), and delete with cleanup.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_label(rest, label_id, name, color=""):
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": label_id, "name": name, "color": color},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _get_label(rest, label_id):
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    return next((l for l in resp.json() if l["label_id"] == label_id), None)


# ── Label CRUD ───────────────────────────────────────────

async def test_create_label(rest):
    """POST /api/labels creates a label."""
    tag = uuid.uuid4().hex[:8]
    result = await _create_label(rest, f"lbl_{tag}", f"Label {tag}")
    assert result["result"] == "ok"


async def test_label_appears_in_list(rest):
    """Created label appears in GET /api/labels."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_list_{tag}"
    await _create_label(rest, lid, f"Listed {tag}")
    label = await _get_label(rest, lid)
    assert label is not None
    assert label["name"] == f"Listed {tag}"


async def test_label_has_color(rest):
    """Label in list has correct color."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_color_{tag}"
    await _create_label(rest, lid, f"Colored {tag}", color="#ff0000")
    label = await _get_label(rest, lid)
    assert label["color"] == "#ff0000"


async def test_label_default_color_empty(rest):
    """Label without color has empty string."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_nocolor_{tag}"
    await _create_label(rest, lid, f"No Color {tag}")
    label = await _get_label(rest, lid)
    assert label["color"] == ""


async def test_delete_label(rest):
    """DELETE /api/labels/{label_id} removes the label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_del_{tag}"
    await _create_label(rest, lid, "To Delete")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    label = await _get_label(rest, lid)
    assert label is None


async def test_label_upsert_updates_name(rest):
    """Creating label with same ID updates the name."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_upsert_{tag}"
    await _create_label(rest, lid, "Original")
    await _create_label(rest, lid, "Updated")
    label = await _get_label(rest, lid)
    assert label["name"] == "Updated"


# ── Entity Assignment ────────────────────────────────────

async def test_assign_entity_to_label(rest):
    """POST /api/labels/{lid}/entities/{eid} assigns entity."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_assign_{tag}"
    eid = f"sensor.lbl_ent_{tag}"
    await _create_label(rest, lid, f"Assign {tag}")
    await rest.set_state(eid, "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_assigned_entity_in_label(rest):
    """Assigned entity appears in label's entities array."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_inlist_{tag}"
    eid = f"sensor.lbl_il_{tag}"
    await _create_label(rest, lid, f"In List {tag}")
    await rest.set_state(eid, "99")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    label = await _get_label(rest, lid)
    assert eid in label["entities"]


async def test_label_entity_count(rest):
    """Label entity_count reflects assigned entities."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_cnt_{tag}"
    await _create_label(rest, lid, f"Count {tag}")
    for i in range(3):
        eid = f"sensor.lbl_c{i}_{tag}"
        await rest.set_state(eid, str(i))
        await rest.client.post(
            f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
            headers=rest._headers(),
        )
    label = await _get_label(rest, lid)
    assert label["entity_count"] == 3


async def test_unassign_entity_from_label(rest):
    """DELETE unassign removes entity from label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_unassign_{tag}"
    eid = f"sensor.lbl_ua_{tag}"
    await _create_label(rest, lid, f"Unassign {tag}")
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    label = await _get_label(rest, lid)
    assert eid not in label["entities"]


# ── Search by Label ──────────────────────────────────────

async def test_search_by_label(rest):
    """GET /api/states/search?label=X returns labeled entities."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_search_{tag}"
    eid = f"sensor.lbl_srch_{tag}"
    await _create_label(rest, lid, f"Search {tag}")
    await rest.set_state(eid, "42")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={lid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_search_by_label_excludes_others(rest):
    """Search by label excludes entities with different labels."""
    tag = uuid.uuid4().hex[:8]
    lid1 = f"lbl_exc1_{tag}"
    lid2 = f"lbl_exc2_{tag}"
    eid1 = f"sensor.lbl_e1_{tag}"
    eid2 = f"sensor.lbl_e2_{tag}"
    await _create_label(rest, lid1, "Label A")
    await _create_label(rest, lid2, "Label B")
    await rest.set_state(eid1, "1")
    await rest.set_state(eid2, "2")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid1}/entities/{eid1}",
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid2}/entities/{eid2}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={lid1}",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid1 in eids
    assert eid2 not in eids


# ── Error Cases ──────────────────────────────────────────

async def test_create_label_missing_name_fails(rest):
    """Label creation without name returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lbl_noname_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_create_label_missing_id_fails(rest):
    """Label creation without label_id returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"name": f"No ID {tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400
