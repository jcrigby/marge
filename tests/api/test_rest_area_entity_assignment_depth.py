"""
CTS -- REST Area Entity Assignment Depth Tests

Tests area entity assignment and unassignment via REST:
POST /api/areas/<aid>/entities/<eid> and DELETE.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Assign Entity to Area ───────────────────────────────

async def test_assign_entity_to_area(rest):
    """POST assigns entity to area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_asgn_{tag}"
    eid = f"sensor.asgn_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Room {tag}"},
    )
    await rest.set_state(eid, "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_assigned_entity_appears_in_area(rest):
    """Assigned entity appears in area entity listing."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_appear_{tag}"
    eid = f"sensor.appear_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Room {tag}"},
    )
    await rest.set_state(eid, "1")
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


# ── Unassign Entity from Area ───────────────────────────

async def test_unassign_entity_from_area(rest):
    """DELETE removes entity from area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_unssgn_{tag}"
    eid = f"sensor.unasgn_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Room {tag}"},
    )
    await rest.set_state(eid, "1")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    del_resp = await rest.client.delete(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid not in eids


# ── Multiple Entities in Area ───────────────────────────

async def test_multiple_entities_in_area(rest):
    """Multiple entities can be assigned to same area."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_multi_{tag}"
    eids = [f"sensor.multi_{i}_{tag}" for i in range(3)]
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Multi Room {tag}"},
    )
    for eid in eids:
        await rest.set_state(eid, "1")
        await rest.client.post(
            f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
            headers=rest._headers(),
        )

    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    listed = [e["entity_id"] for e in resp.json()]
    for eid in eids:
        assert eid in listed


# ── Empty Area ──────────────────────────────────────────

async def test_empty_area_entities_list(rest):
    """New area has empty entity list."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_empty_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": aid, "name": f"Empty {tag}"},
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    assert resp.json() == []
