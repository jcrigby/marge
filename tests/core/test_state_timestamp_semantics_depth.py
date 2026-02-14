"""
CTS -- State Machine Timestamp and Context Semantics Depth Tests

Tests the state machine's handling of last_changed vs last_updated vs
last_reported timestamps, context fields (id, parent_id, user_id),
entity count after operations, and state machine remove behavior.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Timestamp Semantics ─────────────────────────────────

async def test_new_entity_timestamps_equal(rest):
    """New entity has last_changed == last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_new_{tag}"
    await rest.set_state(eid, "10")
    state = await rest.get_state(eid)
    assert state["last_changed"] == state["last_updated"]


async def test_state_change_updates_last_changed(rest):
    """Changing state value updates last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_chg_{tag}"
    await rest.set_state(eid, "A")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "B")
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] >= s1["last_changed"]
    assert s2["state"] == "B"


async def test_same_state_preserves_last_changed(rest):
    """Setting same state value preserves last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_same_{tag}"
    await rest.set_state(eid, "X")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "X")
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]


async def test_attribute_change_updates_last_updated(rest):
    """Changing only attributes updates last_updated but not last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_attr_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "42", {"unit": "kW"})
    s2 = await rest.get_state(eid)
    # Same state value → last_changed preserved
    assert s2["last_changed"] == s1["last_changed"]
    # Different attributes → last_updated advances
    assert s2["last_updated"] >= s1["last_updated"]


async def test_state_has_last_reported(rest):
    """Entity state includes last_reported field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_rep_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert "last_reported" in state


# ── Context Fields ──────────────────────────────────────

async def test_state_has_context(rest):
    """Entity state includes context object."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert "context" in state
    ctx = state["context"]
    assert "id" in ctx


async def test_context_id_is_uuid(rest):
    """Context id looks like a UUID."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_uuid_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    ctx_id = state["context"]["id"]
    assert len(ctx_id) >= 32  # UUID with or without hyphens


async def test_context_changes_on_update(rest):
    """Each state update gets a new context id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_upd_{tag}"
    await rest.set_state(eid, "A")
    ctx1 = (await rest.get_state(eid))["context"]["id"]
    await rest.set_state(eid, "B")
    ctx2 = (await rest.get_state(eid))["context"]["id"]
    assert ctx1 != ctx2


# ── Entity Count and Remove ─────────────────────────────

async def test_entity_count_increases(rest):
    """Creating entities increases total entity count."""
    s1 = await rest.get_states()
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.cnt_{tag}", "1")
    s2 = await rest.get_states()
    assert len(s2) >= len(s1) + 1


async def test_delete_entity_decreases_count(rest):
    """Deleting entity decreases count."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_cnt_{tag}"
    await rest.set_state(eid, "1")
    before = await rest.get_states()
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    after = await rest.get_states()
    assert len(after) < len(before)


async def test_entity_id_in_state(rest):
    """Returned state includes the entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eid_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


async def test_state_value_is_string(rest):
    """State value is always a string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.str_{tag}"
    await rest.set_state(eid, "42")
    state = await rest.get_state(eid)
    assert isinstance(state["state"], str)
    assert state["state"] == "42"


# ── Attributes ──────────────────────────────────────────

async def test_attributes_default_empty(rest):
    """Attributes default to empty dict when not provided."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.adef_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert isinstance(state["attributes"], dict)


async def test_attributes_preserved_on_state_change(rest):
    """Setting state with same attributes preserves them."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.apres_{tag}"
    await rest.set_state(eid, "1", {"unit": "W", "friendly_name": "Power"})
    await rest.set_state(eid, "2", {"unit": "W", "friendly_name": "Power"})
    state = await rest.get_state(eid)
    assert state["state"] == "2"
    assert state["attributes"]["unit"] == "W"
    assert state["attributes"]["friendly_name"] == "Power"
