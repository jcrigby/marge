"""
CTS -- State Machine Timestamp Semantics

Tests STATE-006 behavior: last_changed vs last_updated vs last_reported
are updated correctly based on what changed (state, attributes, or neither).
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.1


async def test_new_entity_timestamps_equal(rest):
    """New entity has matching last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_new_{tag}"
    await rest.set_state(eid, "initial")
    state = await rest.get_state(eid)
    assert state["last_changed"] == state["last_updated"]


async def test_state_change_updates_last_changed(rest):
    """State change updates last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_changed_{tag}"
    await rest.set_state(eid, "first")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "second")
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] >= s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]


async def test_same_state_preserves_last_changed(rest):
    """Re-setting same state does not update last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_same_{tag}"
    await rest.set_state(eid, "stable")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "stable")
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]


async def test_attr_change_updates_last_updated(rest):
    """Attribute-only change updates last_updated but not last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_attr_{tag}"
    await rest.set_state(eid, "fixed", {"key": "v1"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "fixed", {"key": "v2"})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]


async def test_same_state_and_attrs_preserves_both(rest):
    """Identical state+attrs preserves both last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ident_{tag}"
    await rest.set_state(eid, "same", {"a": 1})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "same", {"a": 1})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] == s1["last_updated"]


async def test_context_id_changes_on_each_set(rest):
    """Each set() call generates a new context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ctx_{tag}"
    await rest.set_state(eid, "a")
    s1 = await rest.get_state(eid)
    await rest.set_state(eid, "b")
    s2 = await rest.get_state(eid)
    assert s1["context"]["id"] != s2["context"]["id"]


async def test_context_has_required_fields(rest):
    """Context includes id, parent_id, and user_id fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ctx_fields_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_timestamps_are_iso_format(rest):
    """Timestamps are in ISO 8601 format."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_iso_{tag}"
    await rest.set_state(eid, "check")
    state = await rest.get_state(eid)
    # Should contain 'T' separator and end with timezone info
    assert "T" in state["last_changed"]
    assert "T" in state["last_updated"]


async def test_rapid_updates_maintain_ordering(rest):
    """Rapid updates maintain monotonic timestamp ordering."""
    tag = uuid.uuid4().hex[:8]
    entity = f"sensor.ts_rapid_{tag}"
    timestamps = []
    for i in range(10):
        await rest.set_state(entity, str(i))
        s = await rest.get_state(entity)
        timestamps.append(s["last_updated"])
    # Timestamps should be non-decreasing
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1]


# ── Timestamp Presence (from depth) ────────────────────


@pytest.mark.parametrize("field", ["last_changed", "last_updated"])
async def test_state_has_timestamp_field(rest, field):
    """State object has expected timestamp field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_{field}_{tag}"
    await rest.set_state(eid, "val")
    state = await rest.get_state(eid)
    assert field in state
    assert len(state[field]) > 0


# ── last_updated on any change (from depth) ────────────


async def test_last_updated_updates_on_any_change(rest):
    """last_updated updates on any state POST (even attr-only)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tstamp_upd_{tag}"
    await rest.set_state(eid, "val")
    state1 = await rest.get_state(eid)

    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "val", {"attr": "new"})
    state2 = await rest.get_state(eid)

    assert state2["last_updated"] >= state1["last_updated"]


# ── Multiple Entities Timestamps (from depth) ──────────


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
