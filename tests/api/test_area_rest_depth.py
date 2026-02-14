"""
CTS -- Area REST API Depth Tests

Tests GET/POST/DELETE /api/areas, entity-to-area assignment,
area entity listing, and validation edge cases.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_area(rest):
    """POST /api/areas creates an area."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"area_{tag}", "name": f"Room {tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


async def test_list_areas(rest):
    """GET /api/areas returns area list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"area_list_{tag}", "name": f"List Room {tag}"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    areas = resp.json()
    assert isinstance(areas, list)
    ids = [a["area_id"] for a in areas]
    assert f"area_list_{tag}" in ids


async def test_area_has_fields(rest):
    """Area entries have expected fields."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"area_fld_{tag}", "name": "Full Area"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    found = [a for a in areas if a["area_id"] == f"area_fld_{tag}"]
    assert len(found) == 1
    area = found[0]
    assert area["name"] == "Full Area"
    assert "entity_count" in area
    assert "entities" in area


async def test_delete_area(rest):
    """DELETE /api/areas/{id} removes an area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Delete Me"},
        headers=rest._headers(),
    )

    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    ids = [a["area_id"] for a in resp2.json()]
    assert aid not in ids


async def test_assign_entity_to_area(rest):
    """POST /api/areas/{aid}/entities/{eid} assigns entity."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_assign_{tag}"
    eid = f"sensor.area_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Assign Area"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_area_entities(rest):
    """GET /api/areas/{aid}/entities returns assigned entities."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_ent_list_{tag}"
    eid = f"sensor.area_list_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Entity List Area"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entities = resp.json()
    assert isinstance(entities, list)
    entity_ids = [e.get("entity_id", "") for e in entities]
    assert eid in entity_ids


async def test_unassign_entity_from_area(rest):
    """DELETE /api/areas/{aid}/entities/{eid} unassigns entity."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_unassign_{tag}"
    eid = f"sensor.area_un_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Unassign Area"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_area_entity_count_updates(rest):
    """Area entity_count reflects assignments."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_cnt_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Count Area"},
        headers=rest._headers(),
    )

    for i in range(3):
        eid = f"sensor.area_cnt_ent_{tag}_{i}"
        await rest.set_state(eid, "on")
        await rest.client.post(
            f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
            json={},
            headers=rest._headers(),
        )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    found = [a for a in resp.json() if a["area_id"] == aid]
    assert found[0]["entity_count"] >= 3


async def test_area_upsert(rest):
    """POST /api/areas with same ID updates name."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_upsert_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Original"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Updated"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    found = [a for a in resp.json() if a["area_id"] == aid]
    assert found[0]["name"] == "Updated"


async def test_delete_area_unassigns_entities(rest):
    """Deleting an area unassigns all its entities."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_delun_{tag}"
    eid = f"sensor.area_delun_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": "Delete Unassign"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    # Delete the area
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}",
        headers=rest._headers(),
    )

    # Entity should no longer be assigned to this area
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    areas = resp.json()
    for area in areas:
        assert eid not in area.get("entities", [])


async def test_area_missing_id_400(rest):
    """POST /api/areas without area_id returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"name": "No ID"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_area_missing_name_400(rest):
    """POST /api/areas without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": "no_name_area"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400
