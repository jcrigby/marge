"""
CTS -- Delete + Recreate Cycle Depth Tests

Tests entity lifecycle: create, delete, recreate, verify state is
fresh; bulk delete behavior; delete nonexistent; delete response format.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Delete ──────────────────────────────────────────

async def test_delete_returns_message(rest):
    """DELETE /api/states/{eid} returns a message."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_msg_{tag}"
    await rest.set_state(eid, "1")

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


async def test_delete_nonexistent_returns_404(rest):
    """DELETE for nonexistent entity returns 404."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_noex_{tag}"
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_removes_from_states(rest):
    """Deleted entity no longer in GET /api/states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_gone_{tag}"
    await rest.set_state(eid, "1")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    states = await rest.get_states()
    eids = {s["entity_id"] for s in states}
    assert eid not in eids


async def test_delete_entity_get_returns_404(rest):
    """GET after delete returns 404."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_get404_{tag}"
    await rest.set_state(eid, "1")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Delete + Recreate Cycle ───────────────────────────────

async def test_recreate_after_delete(rest):
    """Entity can be recreated after deletion."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_recreate_{tag}"
    await rest.set_state(eid, "original", {"version": 1})

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "recreated", {"version": 2})
    state = await rest.get_state(eid)
    assert state["state"] == "recreated"
    assert state["attributes"]["version"] == 2


async def test_recreated_entity_fresh_context(rest):
    """Recreated entity gets a new context id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_freshctx_{tag}"

    await rest.set_state(eid, "v1")
    s1 = await rest.get_state(eid)
    ctx1 = s1["context"]["id"]

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "v2")
    s2 = await rest.get_state(eid)
    ctx2 = s2["context"]["id"]

    assert ctx1 != ctx2


async def test_recreated_entity_no_old_attrs(rest):
    """Recreated entity doesn't inherit old attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_noold_{tag}"

    await rest.set_state(eid, "1", {"old_key": "old_val"})
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "2", {"new_key": "new_val"})
    state = await rest.get_state(eid)
    assert "old_key" not in state["attributes"]
    assert state["attributes"]["new_key"] == "new_val"


async def test_delete_recreate_multiple_cycles(rest):
    """Entity survives multiple delete/recreate cycles."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.drc_multi_{tag}"

    for i in range(5):
        await rest.set_state(eid, str(i))
        state = await rest.get_state(eid)
        assert state["state"] == str(i)

        await rest.client.delete(
            f"{rest.base_url}/api/states/{eid}",
            headers=rest._headers(),
        )

        resp = await rest.client.get(
            f"{rest.base_url}/api/states/{eid}",
            headers=rest._headers(),
        )
        assert resp.status_code == 404


# ── Bulk Delete ───────────────────────────────────────────

async def test_delete_multiple_entities(rest):
    """Multiple entities can be deleted independently."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"sensor.drc_bulk_{i}_{tag}" for i in range(5)]
    for eid in eids:
        await rest.set_state(eid, "val")

    for eid in eids:
        resp = await rest.client.delete(
            f"{rest.base_url}/api/states/{eid}",
            headers=rest._headers(),
        )
        assert resp.status_code == 200

    states = await rest.get_states()
    listed = {s["entity_id"] for s in states}
    for eid in eids:
        assert eid not in listed


async def test_delete_one_preserves_others(rest):
    """Deleting one entity doesn't affect others."""
    tag = uuid.uuid4().hex[:8]
    eid_keep = f"sensor.drc_keep_{tag}"
    eid_del = f"sensor.drc_del_{tag}"
    await rest.set_state(eid_keep, "keep")
    await rest.set_state(eid_del, "delete")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid_del}",
        headers=rest._headers(),
    )

    state = await rest.get_state(eid_keep)
    assert state["state"] == "keep"
