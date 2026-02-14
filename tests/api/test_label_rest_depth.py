"""
CTS -- Label REST API Depth Tests

Tests GET/POST/DELETE /api/labels, entity-to-label assignment,
label listing with entity counts, and validation.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_label(rest):
    """POST /api/labels creates a label."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lbl_{tag}", "name": f"Label {tag}", "color": "#ff0000"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


async def test_list_labels(rest):
    """GET /api/labels returns label list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lbl_list_{tag}", "name": f"List Label {tag}"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    labels = resp.json()
    assert isinstance(labels, list)
    ids = [l["label_id"] for l in labels]
    assert f"lbl_list_{tag}" in ids


async def test_label_has_fields(rest):
    """Label entries have expected fields."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lbl_fld_{tag}", "name": "Full Label", "color": "#00ff00"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    labels = resp.json()
    found = [l for l in labels if l["label_id"] == f"lbl_fld_{tag}"]
    assert len(found) == 1
    lbl = found[0]
    assert lbl["name"] == "Full Label"
    assert lbl["color"] == "#00ff00"
    assert "entity_count" in lbl
    assert "entities" in lbl


async def test_delete_label(rest):
    """DELETE /api/labels/{id} removes a label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Delete Me"},
        headers=rest._headers(),
    )

    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    ids = [l["label_id"] for l in resp2.json()]
    assert lid not in ids


async def test_assign_label_to_entity(rest):
    """POST /api/labels/{lid}/entities/{eid} assigns label."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_assign_{tag}"
    eid = f"sensor.lbl_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Assign Label"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Label should show entity
    resp2 = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    labels = resp2.json()
    found = [l for l in labels if l["label_id"] == lid]
    assert len(found) == 1
    assert eid in found[0]["entities"]


async def test_unassign_label_from_entity(rest):
    """DELETE /api/labels/{lid}/entities/{eid} removes assignment."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_unassign_{tag}"
    eid = f"sensor.lbl_unent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Unassign Label"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.delete(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    labels = resp2.json()
    found = [l for l in labels if l["label_id"] == lid]
    if len(found) > 0:
        assert eid not in found[0]["entities"]


async def test_label_entity_count(rest):
    """Label entity_count reflects number of assigned entities."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_cnt_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Count Label"},
        headers=rest._headers(),
    )

    for i in range(3):
        eid = f"sensor.lbl_cnt_ent_{tag}_{i}"
        await rest.set_state(eid, "on")
        await rest.client.post(
            f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
            json={},
            headers=rest._headers(),
        )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    found = [l for l in resp.json() if l["label_id"] == lid]
    assert found[0]["entity_count"] >= 3


async def test_label_upsert(rest):
    """POST /api/labels with same ID updates name/color."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_upsert_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Original", "color": "#000000"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "Updated", "color": "#ffffff"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    found = [l for l in resp.json() if l["label_id"] == lid]
    assert found[0]["name"] == "Updated"
    assert found[0]["color"] == "#ffffff"


async def test_label_missing_name_400(rest):
    """POST /api/labels without name returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"lbl_noname_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_label_missing_id_400(rest):
    """POST /api/labels without label_id returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"name": "No ID Label"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_label_default_color(rest):
    """Label created without color gets empty string default."""
    tag = uuid.uuid4().hex[:8]
    lid = f"lbl_nocolor_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": "No Color"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    found = [l for l in resp.json() if l["label_id"] == lid]
    assert found[0]["color"] == ""
