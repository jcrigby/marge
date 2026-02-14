"""
CTS -- REST /api/states Bulk Operations Tests

Tests GET /api/states (all entities), response format validation,
DELETE lifecycle, and state listing consistency.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/states ─────────────────────────────────────────

async def test_get_all_states_returns_list(rest):
    """GET /api/states returns a JSON array."""
    states = await rest.get_states()
    assert isinstance(states, list)


async def test_get_all_states_nonempty(rest):
    """GET /api/states returns at least one entity."""
    states = await rest.get_states()
    assert len(states) >= 1


async def test_state_entry_has_entity_id(rest):
    """Each state entry has entity_id field."""
    states = await rest.get_states()
    for s in states[:10]:  # Spot-check first 10
        assert "entity_id" in s
        assert "." in s["entity_id"]  # domain.object_id format


async def test_state_entry_has_state(rest):
    """Each state entry has state string field."""
    states = await rest.get_states()
    for s in states[:10]:
        assert "state" in s
        assert isinstance(s["state"], str)


async def test_state_entry_has_attributes(rest):
    """Each state entry has attributes dict."""
    states = await rest.get_states()
    for s in states[:10]:
        assert "attributes" in s
        assert isinstance(s["attributes"], dict)


async def test_state_entry_has_timestamps(rest):
    """Each state entry has last_changed and last_updated."""
    states = await rest.get_states()
    for s in states[:10]:
        assert "last_changed" in s
        assert "last_updated" in s


async def test_state_entry_has_context(rest):
    """Each state entry has context with id."""
    states = await rest.get_states()
    for s in states[:10]:
        assert "context" in s
        assert "id" in s["context"]


async def test_created_entity_in_get_all(rest):
    """Newly created entity appears in GET /api/states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.bulk_{tag}"
    await rest.set_state(eid, "present")

    states = await rest.get_states()
    entity_ids = [s["entity_id"] for s in states]
    assert eid in entity_ids


# ── DELETE /api/states/:entity_id ────────────────────────

async def test_delete_entity_returns_200(rest):
    """DELETE /api/states/:entity_id returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_{tag}"
    await rest.set_state(eid, "to_delete")

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_delete_entity_removes_from_states(rest):
    """Deleted entity no longer in GET /api/states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_rm_{tag}"
    await rest.set_state(eid, "will_vanish")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state is None


async def test_delete_entity_then_recreate(rest):
    """Deleted entity can be recreated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_re_{tag}"
    await rest.set_state(eid, "first")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    await rest.set_state(eid, "second")
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "second"


async def test_delete_nonexistent_entity(rest):
    """DELETE nonexistent entity returns 200 (idempotent)."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.never_existed_bulk_999",
        headers=rest._headers(),
    )
    # Should either 200 (idempotent) or 404
    assert resp.status_code in (200, 404)


# ── Consistency ──────────────────────────────────────────

async def test_set_and_get_consistency(rest):
    """POST then GET returns same state and attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.consist_{tag}"
    await rest.set_state(eid, "exact_value", {"key": "exact_attr"})

    state = await rest.get_state(eid)
    assert state["state"] == "exact_value"
    assert state["attributes"]["key"] == "exact_attr"


async def test_multiple_entities_unique(rest):
    """Multiple created entities are distinct."""
    tag = uuid.uuid4().hex[:8]
    for i in range(5):
        await rest.set_state(f"sensor.uniq_{tag}_{i}", str(i))

    for i in range(5):
        state = await rest.get_state(f"sensor.uniq_{tag}_{i}")
        assert state["state"] == str(i)
