"""
CTS -- Label Registry REST API Depth Tests

Tests the full label management lifecycle: create labels, list labels,
assign labels to entities, search by label, unassign labels, delete
labels. Verifies entity counts, color attributes, and list contents.
"""

import asyncio
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


async def _delete_label(rest, label_id):
    return await rest.client.delete(
        f"{rest.base_url}/api/labels/{label_id}",
        headers=rest._headers(),
    )


async def _assign_label(rest, label_id, entity_id):
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{label_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _unassign_label(rest, label_id, entity_id):
    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/{label_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _list_labels(rest):
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Label CRUD ────────────────────────────────────────────

async def test_create_label(rest):
    """POST /api/labels creates a new label."""
    tag = uuid.uuid4().hex[:8]
    result = await _create_label(rest, f"lbl_{tag}", f"Critical {tag}", "#ff0000")
    assert result["result"] == "ok"


async def test_label_appears_in_list(rest):
    """Created label appears in GET /api/labels."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_list_{tag}"
    await _create_label(rest, lid, f"Info {tag}")
    labels = await _list_labels(rest)
    lids = [l["label_id"] for l in labels]
    assert lid in lids


async def test_label_has_name_and_color(rest):
    """Label in list has correct name and color."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_nc_{tag}"
    await _create_label(rest, lid, f"Warning {tag}", "#ffaa00")
    labels = await _list_labels(rest)
    label = next(l for l in labels if l["label_id"] == lid)
    assert label["name"] == f"Warning {tag}"
    assert label["color"] == "#ffaa00"


async def test_delete_label(rest):
    """DELETE /api/labels/{label_id} removes the label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_del_{tag}"
    await _create_label(rest, lid, f"Temp {tag}")
    resp = await _delete_label(rest, lid)
    assert resp.status_code == 200
    labels = await _list_labels(rest)
    lids = [l["label_id"] for l in labels]
    assert lid not in lids


# ── Label Entity Assignment ───────────────────────────────

async def test_assign_label_to_entity(rest):
    """POST assigns a label to an entity."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_assign_{tag}"
    eid = f"sensor.lbl_{tag}"
    await _create_label(rest, lid, f"Test {tag}")
    await rest.set_state(eid, "42")
    result = await _assign_label(rest, lid, eid)
    assert result["result"] == "ok"


async def test_assigned_entity_in_label_list(rest):
    """Assigned entity appears in label's entity list."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_elist_{tag}"
    eid = f"light.lbl_elist_{tag}"
    await _create_label(rest, lid, f"Test {tag}")
    await rest.set_state(eid, "on")
    await _assign_label(rest, lid, eid)
    labels = await _list_labels(rest)
    label = next(l for l in labels if l["label_id"] == lid)
    assert eid in label["entities"]


async def test_label_entity_count(rest):
    """Label entity_count reflects assigned entities."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_cnt_{tag}"
    await _create_label(rest, lid, f"Multi {tag}")
    await rest.set_state(f"sensor.lc1_{tag}", "1")
    await rest.set_state(f"sensor.lc2_{tag}", "2")
    await rest.set_state(f"sensor.lc3_{tag}", "3")
    await _assign_label(rest, lid, f"sensor.lc1_{tag}")
    await _assign_label(rest, lid, f"sensor.lc2_{tag}")
    await _assign_label(rest, lid, f"sensor.lc3_{tag}")
    labels = await _list_labels(rest)
    label = next(l for l in labels if l["label_id"] == lid)
    assert label["entity_count"] == 3


async def test_unassign_label(rest):
    """DELETE unassigns a label from an entity."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_un_{tag}"
    eid = f"switch.lbl_un_{tag}"
    await _create_label(rest, lid, f"Unassign {tag}")
    await rest.set_state(eid, "on")
    await _assign_label(rest, lid, eid)
    await _unassign_label(rest, lid, eid)
    labels = await _list_labels(rest)
    label = next(l for l in labels if l["label_id"] == lid)
    assert eid not in label["entities"]


# ── Search by Label ───────────────────────────────────────

async def test_search_by_label(rest):
    """GET /api/states/search?label=X returns labeled entities."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_srch_{tag}"
    eid = f"sensor.lbl_srch_{tag}"
    await _create_label(rest, lid, f"Search {tag}")
    await rest.set_state(eid, "77")
    await _assign_label(rest, lid, eid)
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={lid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid in eids


async def test_search_by_label_excludes_other(rest):
    """Search by label doesn't include entities with other labels."""
    tag = uuid.uuid4().hex[:8]
    lid1 = f"lbl_ex1_{tag}"
    lid2 = f"lbl_ex2_{tag}"
    eid1 = f"sensor.lex1_{tag}"
    eid2 = f"sensor.lex2_{tag}"
    await _create_label(rest, lid1, "Label 1")
    await _create_label(rest, lid2, "Label 2")
    await rest.set_state(eid1, "1")
    await rest.set_state(eid2, "2")
    await _assign_label(rest, lid1, eid1)
    await _assign_label(rest, lid2, eid2)
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={lid1}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid1 in eids
    assert eid2 not in eids


# ── Full Lifecycle ────────────────────────────────────────

async def test_label_full_lifecycle(rest):
    """Label lifecycle: create → assign → search → unassign → delete."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_life_{tag}"
    eid = f"sensor.lbl_life_{tag}"

    await _create_label(rest, lid, f"Lifecycle {tag}", "#00ff00")
    await rest.set_state(eid, "100")
    await _assign_label(rest, lid, eid)

    # Verify assignment
    labels = await _list_labels(rest)
    label = next(l for l in labels if l["label_id"] == lid)
    assert eid in label["entities"]

    # Verify search
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={lid}",
        headers=rest._headers(),
    )
    assert any(e["entity_id"] == eid for e in resp.json())

    # Unassign and delete
    await _unassign_label(rest, lid, eid)
    resp = await _delete_label(rest, lid)
    assert resp.status_code == 200
