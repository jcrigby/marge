"""
CTS -- Area and Label REST API Depth Tests

Tests area CRUD with entity assignment, label CRUD with
entity assignment, cross-references, and search integration.
"""

import pytest

pytestmark = pytest.mark.asyncio

_AREA_PREFIX = "cts_aldepth"
_LABEL_PREFIX = "cts_lbl_depth"


# ── Area CRUD ────────────────────────────────────────────────

async def test_area_create(rest):
    """POST /api/areas creates an area."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_kitchen", "name": "Kitchen"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_list_after_create(rest):
    """Created area appears in GET /api/areas."""
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_living", "name": "Living Room"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [a["area_id"] for a in data]
    assert f"{_AREA_PREFIX}_living" in ids


async def test_area_has_name_and_count(rest):
    """Area entries include name and entity_count fields."""
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_fmt", "name": "Format Test"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    data = resp.json()
    area = next(a for a in data if a["area_id"] == f"{_AREA_PREFIX}_fmt")
    assert area["name"] == "Format Test"
    assert "entity_count" in area


async def test_area_assign_entity(rest):
    """Assigning entity to area works."""
    await rest.set_state("sensor.area_assign_test", "ok")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_assign", "name": "Assign Test"},
        headers=rest._headers(),
    )
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_assign/entities/sensor.area_assign_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_entity_list(rest):
    """GET /api/areas/:id/entities returns assigned entities."""
    await rest.set_state("sensor.area_list_e1", "1")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_elist", "name": "Entity List"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_elist/entities/sensor.area_list_e1",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_elist/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.area_list_e1" in ids


async def test_area_unassign_entity(rest):
    """DELETE unassigns entity from area."""
    await rest.set_state("sensor.area_unassign", "1")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_unassign", "name": "Unassign Test"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_unassign/entities/sensor.area_unassign",
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_unassign/entities/sensor.area_unassign",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Verify entity no longer in area
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_unassign/entities",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.area_unassign" not in ids


async def test_area_delete(rest):
    """DELETE /api/areas/:id removes area."""
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_del", "name": "Delete Me"},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_del",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_create_missing_fields(rest):
    """Creating area without required fields returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_noname"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_area_search_filter(rest):
    """Search by area filter returns only entities in that area."""
    await rest.set_state("sensor.area_search_in", "1")
    await rest.set_state("sensor.area_search_out", "1")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"{_AREA_PREFIX}_search", "name": "Search Test"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/{_AREA_PREFIX}_search/entities/sensor.area_search_in",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={_AREA_PREFIX}_search",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.area_search_in" in ids
    assert "sensor.area_search_out" not in ids


# ── Label CRUD ───────────────────────────────────────────────

async def test_label_create(rest):
    """POST /api/labels creates a label."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_critical", "name": "Critical", "color": "#ff0000"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_list_after_create(rest):
    """Created label appears in GET /api/labels."""
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_list", "name": "Listed"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [l["label_id"] for l in data]
    assert f"{_LABEL_PREFIX}_list" in ids


async def test_label_has_color_and_count(rest):
    """Label entries include color and entity_count fields."""
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_fmt", "name": "Format", "color": "#00ff00"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    data = resp.json()
    label = next(l for l in data if l["label_id"] == f"{_LABEL_PREFIX}_fmt")
    assert label["color"] == "#00ff00"
    assert "entity_count" in label


async def test_label_assign_entity(rest):
    """Assigning label to entity works."""
    await rest.set_state("sensor.label_assign_test", "ok")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_assign", "name": "Assign"},
        headers=rest._headers(),
    )
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_assign/entities/sensor.label_assign_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_entity_appears_in_list(rest):
    """Assigned entity appears in label's entities list."""
    await rest.set_state("sensor.label_elist", "ok")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_elist", "name": "EList"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_elist/entities/sensor.label_elist",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/labels",
        headers=rest._headers(),
    )
    data = resp.json()
    label = next(l for l in data if l["label_id"] == f"{_LABEL_PREFIX}_elist")
    assert "sensor.label_elist" in label["entities"]
    assert label["entity_count"] >= 1


async def test_label_unassign_entity(rest):
    """DELETE unassigns label from entity."""
    await rest.set_state("sensor.label_unassign", "ok")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_unassign", "name": "Unassign"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_unassign/entities/sensor.label_unassign",
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_unassign/entities/sensor.label_unassign",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_delete(rest):
    """DELETE /api/labels/:id removes label."""
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_del", "name": "Delete"},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_del",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_label_search_filter(rest):
    """Search by label filter returns only labeled entities."""
    await rest.set_state("sensor.label_search_in", "1")
    await rest.set_state("sensor.label_search_out", "1")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": f"{_LABEL_PREFIX}_search", "name": "SearchLabel"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels/{_LABEL_PREFIX}_search/entities/sensor.label_search_in",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={_LABEL_PREFIX}_search",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert "sensor.label_search_in" in ids
    assert "sensor.label_search_out" not in ids
