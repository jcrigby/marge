"""
CTS -- REST Area CRUD Depth Tests

Tests REST /api/areas endpoints: list, create, delete, area entity
listing, assign entity to area, unassign entity from area.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── List Areas ───────────────────────────────────────────

async def test_list_areas_returns_200(rest):
    """GET /api/areas returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_areas_returns_array(rest):
    """GET /api/areas returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    assert isinstance(resp.json(), list)


# ── Create Area ──────────────────────────────────────────

async def test_create_area_success(rest):
    """POST /api/areas creates area."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": f"area_{tag}", "name": f"Room {tag}"},
    )
    assert resp.status_code == 200


async def test_create_area_appears_in_list(rest):
    """Created area appears in GET /api/areas."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_crud_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Room {tag}"},
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area_ids = [a["area_id"] for a in resp.json()]
    assert aid in area_ids


async def test_area_entry_has_name(rest):
    """Area entry has name field."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_name_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Kitchen {tag}"},
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area = next(a for a in resp.json() if a["area_id"] == aid)
    assert area["name"] == f"Kitchen {tag}"


# ── Delete Area ──────────────────────────────────────────

async def test_delete_area_removes_from_list(rest):
    """DELETE /api/areas/<id> removes area from list."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Temp"},
    )
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area_ids = [a["area_id"] for a in resp.json()]
    assert aid not in area_ids


# ── Entity Assignment ────────────────────────────────────

async def test_assign_entity_to_area(rest):
    """POST /api/areas/<aid>/entities/<eid> assigns entity."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_asgn_{tag}"
    eid = f"sensor.area_test_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Test Room"},
    )
    await rest.set_state(eid, "1")

    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_assigned_entity_in_area_entities(rest):
    """Assigned entity appears in GET /api/areas/<aid>/entities."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_elist_{tag}"
    eid = f"sensor.area_el_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "List Room"},
    )
    await rest.set_state(eid, "50")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_unassign_entity_removes_from_area(rest):
    """DELETE /api/areas/<aid>/entities/<eid> removes entity from area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_unsgn_{tag}"
    eid = f"sensor.area_un_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Remove Room"},
    )
    await rest.set_state(eid, "v")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid not in eids


async def test_area_entity_count(rest):
    """Area listing includes correct entity_count."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_cnt_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": "Count Room"},
    )
    for i in range(3):
        eid = f"sensor.area_cnt_{i}_{tag}"
        await rest.set_state(eid, str(i))
        await rest.client.post(
            f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
            headers=rest._headers(),
        )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    area = next(a for a in resp.json() if a["area_id"] == aid)
    assert area["entity_count"] == 3
