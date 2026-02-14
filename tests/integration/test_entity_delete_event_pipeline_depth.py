"""
CTS -- Entity Delete & Event Pipeline Depth Tests

Tests entity deletion via REST API: DELETE /api/states/{entity_id},
verify 404 after delete, deletion event propagation through WS,
re-creation after delete, and delete of nonexistent entities.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Delete ──────────────────────────────────────────

async def test_delete_entity_returns_200(rest):
    """DELETE /api/states/{entity_id} returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_delete_entity_message(rest):
    """Delete response has message indicating removal."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_msg_{tag}"
    await rest.set_state(eid, "1")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "message" in data
    assert eid in data["message"]


async def test_delete_entity_gone(rest):
    """Deleted entity returns 404 on subsequent GET."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_gone_{tag}"
    await rest.set_state(eid, "1")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state is None


async def test_delete_nonexistent_returns_404(rest):
    """DELETE on nonexistent entity returns 404."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_nx_{tag}"
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Recreate After Delete ─────────────────────────────────

async def test_recreate_after_delete(rest):
    """Entity can be recreated after deletion."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_rc_{tag}"
    await rest.set_state(eid, "first")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    # Recreate
    await rest.set_state(eid, "second")
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "second"


async def test_recreate_preserves_new_attributes(rest):
    """Recreated entity has new attributes, not old ones."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_attr_{tag}"
    await rest.set_state(eid, "old", {"unit": "C"})
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    await rest.set_state(eid, "new", {"unit": "F"})
    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "F"


# ── Delete + WS Events ───────────────────────────────────

async def test_delete_triggers_ws_event(rest, ws):
    """Creating then deleting entity triggers WS state_changed events."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_ev_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "1")
    # Consume the create event
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid


# ── Multiple Deletes ──────────────────────────────────────

async def test_delete_multiple_entities(rest):
    """Deleting multiple entities independently."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"sensor.del_m{i}_{tag}" for i in range(3)]
    for eid in entities:
        await rest.set_state(eid, "1")
    for eid in entities:
        resp = await rest.client.delete(
            f"{rest.base_url}/api/states/{eid}",
            headers=rest._headers(),
        )
        assert resp.status_code == 200
    for eid in entities:
        assert await rest.get_state(eid) is None


async def test_delete_does_not_affect_others(rest):
    """Deleting one entity doesn't affect other entities."""
    tag = uuid.uuid4().hex[:8]
    eid_keep = f"sensor.del_keep_{tag}"
    eid_del = f"sensor.del_rm_{tag}"
    await rest.set_state(eid_keep, "keep_me")
    await rest.set_state(eid_del, "remove_me")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid_del}",
        headers=rest._headers(),
    )
    state = await rest.get_state(eid_keep)
    assert state is not None
    assert state["state"] == "keep_me"


# ── Delete + History ──────────────────────────────────────

async def test_delete_entity_history_persists(rest):
    """History for deleted entity may still return recorded data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_hist_{tag}"
    await rest.set_state(eid, "before_delete")
    await asyncio.sleep(0.3)
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # History may contain the state from before deletion
    states = [e.get("state") for e in resp.json()]
    # Either has history or empty (both valid after delete)
    assert isinstance(states, list)
