"""
CTS -- REST Service Target Pattern Depth Tests

Tests the alternative target.entity_id pattern for REST service calls,
where entity_id is nested under a "target" key instead of at the top
level. Also tests entity_id as array for multi-entity calls.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _call_service(rest, domain, service, body):
    """Call service and return response JSON."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/{domain}/{service}",
        json=body,
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── target.entity_id String ──────────────────────────────

async def test_target_entity_id_string(rest):
    """Service call with target.entity_id as string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_str_{tag}"
    await rest.set_state(eid, "off")
    result = await _call_service(rest, "light", "turn_on", {
        "target": {"entity_id": eid},
    })
    changed = result.get("changed_states", [])
    assert any(e["entity_id"] == eid for e in changed)
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_target_entity_id_with_data(rest):
    """Service call with target.entity_id + additional service data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tgt_data_{tag}"
    await rest.set_state(eid, "off")
    await _call_service(rest, "light", "turn_on", {
        "target": {"entity_id": eid},
        "brightness": 200,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


# ── target.entity_id Array ───────────────────────────────

async def test_target_entity_id_array(rest):
    """Service call with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.tgt_arr_{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")
    result = await _call_service(rest, "switch", "turn_on", {
        "target": {"entity_id": eids},
    })
    changed = result.get("changed_states", [])
    changed_eids = {e["entity_id"] for e in changed}
    for eid in eids:
        assert eid in changed_eids


async def test_target_array_all_entities_updated(rest):
    """All entities in target array are updated."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.tgt_all_{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")
    await _call_service(rest, "light", "turn_on", {
        "target": {"entity_id": eids},
    })
    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Direct entity_id String vs Target ────────────────────

async def test_direct_entity_id_still_works(rest):
    """Direct entity_id (not in target) still works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.tgt_direct_{tag}"
    await rest.set_state(eid, "off")
    await _call_service(rest, "switch", "turn_on", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_direct_entity_id_array(rest):
    """Direct entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.tgt_darr_{i}_{tag}" for i in range(2)]
    for eid in eids:
        await rest.set_state(eid, "off")
    await _call_service(rest, "light", "turn_on", {
        "entity_id": eids,
    })
    for eid in eids:
        assert (await rest.get_state(eid))["state"] == "on"


# ── Target with Different Domains ────────────────────────

async def test_target_climate_service(rest):
    """target.entity_id works with climate domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.tgt_clim_{tag}"
    await rest.set_state(eid, "off")
    await _call_service(rest, "climate", "set_hvac_mode", {
        "target": {"entity_id": eid},
        "hvac_mode": "heat",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "heat"


async def test_target_cover_service(rest):
    """target.entity_id works with cover domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.tgt_cov_{tag}"
    await rest.set_state(eid, "closed")
    await _call_service(rest, "cover", "open_cover", {
        "target": {"entity_id": eid},
    })
    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_target_lock_service(rest):
    """target.entity_id works with lock domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.tgt_lock_{tag}"
    await rest.set_state(eid, "unlocked")
    await _call_service(rest, "lock", "lock", {
        "target": {"entity_id": eid},
    })
    state = await rest.get_state(eid)
    assert state["state"] == "locked"


# ── No entity_id Returns Empty changed_states ────────────

async def test_no_entity_id_empty_changed(rest):
    """Service call without entity_id returns empty changed_states."""
    result = await _call_service(rest, "light", "turn_on", {})
    assert result.get("changed_states", []) == []


async def test_empty_target_empty_changed(rest):
    """Service call with empty target returns empty changed_states."""
    result = await _call_service(rest, "switch", "turn_on", {
        "target": {},
    })
    assert result.get("changed_states", []) == []
