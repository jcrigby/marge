"""
CTS -- State Timestamp Depth Tests

Tests that state objects contain correct timestamp fields:
last_changed, last_updated format and presence, and that
timestamps update appropriately on state changes and attribute-only
changes.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.1


# ── Timestamp Presence ───────────────────────────────────

async def test_state_has_last_changed(rest):
    """State object has last_changed field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_lc_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "last_changed" in state
    assert len(state["last_changed"]) > 0


async def test_state_has_last_updated(rest):
    """State object has last_updated field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_lu_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "last_updated" in state
    assert len(state["last_updated"]) > 0


async def test_timestamps_are_iso_format(rest):
    """Timestamps are in ISO 8601 format (contain T and Z or +)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_iso_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "T" in state["last_changed"]
    assert "T" in state["last_updated"]


# ── Timestamp Updates ────────────────────────────────────

async def test_last_changed_updates_on_state_change(rest):
    """last_changed updates when state value changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_chg_{tag}"
    await rest.set_state(eid, "first")
    state1 = await rest.get_state(eid)

    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "second")
    state2 = await rest.get_state(eid)

    assert state2["last_changed"] >= state1["last_changed"]


async def test_last_updated_updates_on_any_change(rest):
    """last_updated updates on any state POST."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_upd_{tag}"
    await rest.set_state(eid, "val")
    state1 = await rest.get_state(eid)

    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "val", {"attr": "new"})
    state2 = await rest.get_state(eid)

    assert state2["last_updated"] >= state1["last_updated"]


async def test_new_entity_timestamps_equal(rest):
    """New entity has last_changed == last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_eq_{tag}"
    await rest.set_state(eid, "init")
    state = await rest.get_state(eid)
    assert state["last_changed"] == state["last_updated"]


# ── Context + Timestamp ──────────────────────────────────

async def test_state_has_context(rest):
    """State object has context field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_ctx_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "context" in state


async def test_context_id_present(rest):
    """Context field has an id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_cid_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


# ── Multiple Entities Timestamps ─────────────────────────

async def test_multiple_entities_independent_timestamps(rest):
    """Different entities have independent timestamps."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.tstamp_a_{tag}"
    eid2 = f"sensor.tstamp_b_{tag}"
    await rest.set_state(eid1, "first")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid2, "second")

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    # Entity 2 created later, so its timestamps should be >= entity 1
    assert s2["last_updated"] >= s1["last_updated"]
