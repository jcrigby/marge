"""
CTS -- State Context and Timestamp Semantics Tests

Verifies context.id generation, last_changed only updates on state change,
last_updated updates on state or attribute change, and last_reported
always updates.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_state_has_context_id(rest):
    """Entity state includes context.id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_{tag}"
    await rest.set_state(eid, "42")

    state = await rest.get_state(eid)
    assert "context" in state
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_context_id_is_uuid_format(rest):
    """context.id looks like a UUID (contains dashes)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_uuid_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    ctx_id = state["context"]["id"]
    assert "-" in ctx_id


async def test_context_id_changes_on_update(rest):
    """Each state update generates a new context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_new_{tag}"
    await rest.set_state(eid, "first")
    state1 = await rest.get_state(eid)
    ctx1 = state1["context"]["id"]

    await rest.set_state(eid, "second")
    state2 = await rest.get_state(eid)
    ctx2 = state2["context"]["id"]

    assert ctx1 != ctx2


async def test_last_changed_present(rest):
    """Entity state includes last_changed field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    assert "last_changed" in state
    assert "T" in state["last_changed"]  # ISO 8601 format


async def test_last_updated_present(rest):
    """Entity state includes last_updated field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lu_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    assert "last_updated" in state


async def test_last_changed_only_on_state_change(rest):
    """last_changed only updates when state string changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_same_{tag}"
    await rest.set_state(eid, "stable")
    state1 = await rest.get_state(eid)
    lc1 = state1["last_changed"]

    # Set same state again — last_changed should NOT change
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "stable")
    state2 = await rest.get_state(eid)
    lc2 = state2["last_changed"]

    assert lc1 == lc2


async def test_last_changed_updates_on_state_change(rest):
    """last_changed updates when state string changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_diff_{tag}"
    await rest.set_state(eid, "alpha")
    state1 = await rest.get_state(eid)
    lc1 = state1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "beta")
    state2 = await rest.get_state(eid)
    lc2 = state2["last_changed"]

    assert lc1 != lc2


async def test_last_updated_on_attr_change(rest):
    """last_updated changes when only attributes change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lu_attr_{tag}"
    await rest.set_state(eid, "stable", {"version": 1})
    state1 = await rest.get_state(eid)
    lu1 = state1["last_updated"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "stable", {"version": 2})
    state2 = await rest.get_state(eid)
    lu2 = state2["last_updated"]

    assert lu1 != lu2


async def test_last_changed_stable_on_attr_only_change(rest):
    """last_changed does NOT change when only attributes change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_attr_{tag}"
    await rest.set_state(eid, "stable", {"count": 1})
    state1 = await rest.get_state(eid)
    lc1 = state1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "stable", {"count": 2})
    state2 = await rest.get_state(eid)
    lc2 = state2["last_changed"]

    assert lc1 == lc2


async def test_new_entity_timestamps_all_equal(rest):
    """Brand new entity has all timestamps equal."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.new_ts_{tag}"
    await rest.set_state(eid, "initial")

    state = await rest.get_state(eid)
    lc = state["last_changed"]
    lu = state["last_updated"]
    assert lc == lu
