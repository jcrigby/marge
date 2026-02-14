"""
CTS -- State Delete & Recreate Tests

Tests DELETE /api/states/{entity_id}, GET on nonexistent entities,
recreation after deletion, and delete edge cases.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_delete_entity_returns_200(rest):
    """DELETE /api/states/{entity_id} returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_{tag}"
    await rest.set_state(eid, "exists")

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_deleted_entity_gone_from_list(rest):
    """Deleted entity no longer appears in GET /api/states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_list_{tag}"
    await rest.set_state(eid, "exists")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    entity_ids = [e["entity_id"] for e in resp.json()]
    assert eid not in entity_ids


async def test_get_nonexistent_entity_404(rest):
    """GET /api/states/{nonexistent} returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.never_existed_xyz_abcdef",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_recreate_after_delete(rest):
    """Entity can be recreated after deletion."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_recreate_{tag}"

    await rest.set_state(eid, "first_life")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "second_life")
    state = await rest.get_state(eid)
    assert state["state"] == "second_life"


async def test_recreated_entity_fresh_context(rest):
    """Recreated entity gets a fresh context id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_ctx_{tag}"

    await rest.set_state(eid, "original")
    s1 = await rest.get_state(eid)
    ctx1 = s1["context"]["id"]

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "recreated")
    s2 = await rest.get_state(eid)
    ctx2 = s2["context"]["id"]

    assert ctx1 != ctx2


async def test_delete_preserves_other_entities(rest):
    """Deleting one entity does not affect others."""
    tag = uuid.uuid4().hex[:8]
    eid_keep = f"sensor.del_keep_{tag}"
    eid_drop = f"sensor.del_drop_{tag}"

    await rest.set_state(eid_keep, "kept")
    await rest.set_state(eid_drop, "dropped")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid_drop}",
        headers=rest._headers(),
    )

    state = await rest.get_state(eid_keep)
    assert state["state"] == "kept"


async def test_delete_entity_with_attributes(rest):
    """Entity with attributes can be deleted cleanly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_attrs_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200, "color": "red"})

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp2.status_code == 404


async def test_recreated_entity_starts_clean(rest):
    """Recreated entity has no leftover attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_clean_{tag}"

    await rest.set_state(eid, "on", {"old_key": "old_val"})
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "fresh")
    state = await rest.get_state(eid)
    assert state["state"] == "fresh"
    assert "old_key" not in state.get("attributes", {})


async def test_multiple_deletes_idempotent(rest):
    """Deleting an already-deleted entity still returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_idem_{tag}"
    await rest.set_state(eid, "exists")

    # First delete
    resp1 = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp1.status_code == 200

    # Second delete (already gone)
    resp2 = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    # Should not error — either 200 or 404 is acceptable
    assert resp2.status_code in [200, 404]
