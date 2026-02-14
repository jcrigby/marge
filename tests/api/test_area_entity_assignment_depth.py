"""
CTS -- Area and Entity Assignment REST API Depth Tests

Tests the full area management lifecycle: create area, list areas,
assign entities to areas, list area entities, search by area,
unassign entities, delete areas. Verifies entity counts and list
contents at each step.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_area(rest, area_id, name):
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _delete_area(rest, area_id):
    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}",
        headers=rest._headers(),
    )
    return resp


async def _assign_entity(rest, area_id, entity_id):
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _unassign_entity(rest, area_id, entity_id):
    resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _list_areas(rest):
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _list_area_entities(rest, area_id):
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{area_id}/entities",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Area CRUD ─────────────────────────────────────────────

async def test_create_area(rest):
    """POST /api/areas creates a new area."""
    tag = uuid.uuid4().hex[:8]
    result = await _create_area(rest, f"area_{tag}", f"Test Room {tag}")
    assert result["result"] == "ok"


async def test_create_area_appears_in_list(rest):
    """Created area appears in GET /api/areas."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_list_{tag}"
    await _create_area(rest, aid, f"Listed Room {tag}")
    areas = await _list_areas(rest)
    area_ids = [a["area_id"] for a in areas]
    assert aid in area_ids


async def test_area_has_name(rest):
    """Area in list has correct name."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_name_{tag}"
    await _create_area(rest, aid, f"Kitchen {tag}")
    areas = await _list_areas(rest)
    area = next(a for a in areas if a["area_id"] == aid)
    assert area["name"] == f"Kitchen {tag}"


async def test_delete_area(rest):
    """DELETE /api/areas/{area_id} removes the area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_del_{tag}"
    await _create_area(rest, aid, f"Temp Room {tag}")
    resp = await _delete_area(rest, aid)
    assert resp.status_code == 200
    areas = await _list_areas(rest)
    area_ids = [a["area_id"] for a in areas]
    assert aid not in area_ids


# ── Entity Assignment ─────────────────────────────────────

async def test_assign_entity_to_area(rest):
    """POST /api/areas/{area_id}/entities/{entity_id} assigns entity."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_assign_{tag}"
    eid = f"light.assign_{tag}"
    await _create_area(rest, aid, f"Room {tag}")
    await rest.set_state(eid, "on")
    result = await _assign_entity(rest, aid, eid)
    assert result["result"] == "ok"


async def test_assigned_entity_in_area_list(rest):
    """Assigned entity appears in GET /api/areas/{area_id}/entities."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_alist_{tag}"
    eid = f"sensor.alist_{tag}"
    await _create_area(rest, aid, f"Room {tag}")
    await rest.set_state(eid, "42")
    await _assign_entity(rest, aid, eid)
    entities = await _list_area_entities(rest, aid)
    eids = [e.get("entity_id") for e in entities]
    assert eid in eids


async def test_area_entity_count(rest):
    """Area entity_count reflects assigned entities."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_cnt_{tag}"
    await _create_area(rest, aid, f"Room {tag}")
    await rest.set_state(f"light.cnt1_{tag}", "on")
    await rest.set_state(f"light.cnt2_{tag}", "off")
    await _assign_entity(rest, aid, f"light.cnt1_{tag}")
    await _assign_entity(rest, aid, f"light.cnt2_{tag}")
    areas = await _list_areas(rest)
    area = next(a for a in areas if a["area_id"] == aid)
    assert area["entity_count"] == 2


async def test_unassign_entity_from_area(rest):
    """DELETE unassign removes entity from area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_unassign_{tag}"
    eid = f"switch.unassign_{tag}"
    await _create_area(rest, aid, f"Room {tag}")
    await rest.set_state(eid, "on")
    await _assign_entity(rest, aid, eid)
    await _unassign_entity(rest, aid, eid)
    entities = await _list_area_entities(rest, aid)
    eids = [e.get("entity_id") for e in entities]
    assert eid not in eids


# ── Search by Area ────────────────────────────────────────

async def test_search_by_area(rest):
    """GET /api/states/search?area=X returns only entities in that area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_search_{tag}"
    eid = f"sensor.search_{tag}"
    await _create_area(rest, aid, f"Search Room {tag}")
    await rest.set_state(eid, "99")
    await _assign_entity(rest, aid, eid)
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={aid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid in eids


async def test_search_by_area_excludes_unassigned(rest):
    """Search by area doesn't include entities in other areas."""
    tag = uuid.uuid4().hex[:8]
    aid1 = f"area_exc1_{tag}"
    aid2 = f"area_exc2_{tag}"
    eid1 = f"sensor.exc1_{tag}"
    eid2 = f"sensor.exc2_{tag}"
    await _create_area(rest, aid1, "Room 1")
    await _create_area(rest, aid2, "Room 2")
    await rest.set_state(eid1, "1")
    await rest.set_state(eid2, "2")
    await _assign_entity(rest, aid1, eid1)
    await _assign_entity(rest, aid2, eid2)
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={aid1}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid1 in eids
    assert eid2 not in eids


# ── Full Lifecycle ────────────────────────────────────────

async def test_area_full_lifecycle(rest):
    """Area lifecycle: create → assign → verify → unassign → delete."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_life_{tag}"
    eid = f"light.life_{tag}"

    await _create_area(rest, aid, f"Lifecycle Room {tag}")
    await rest.set_state(eid, "on")
    await _assign_entity(rest, aid, eid)

    entities = await _list_area_entities(rest, aid)
    assert any(e.get("entity_id") == eid for e in entities)

    await _unassign_entity(rest, aid, eid)
    entities = await _list_area_entities(rest, aid)
    assert not any(e.get("entity_id") == eid for e in entities)

    resp = await _delete_area(rest, aid)
    assert resp.status_code == 200
