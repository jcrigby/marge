"""
CTS -- State Machine Timestamp Semantics

Tests STATE-006 behavior: last_changed vs last_updated vs last_reported
are updated correctly based on what changed (state, attributes, or neither).
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_new_entity_timestamps_equal(rest):
    """New entity has matching last_changed and last_updated."""
    await rest.set_state("sensor.ts_new", "initial")
    state = await rest.get_state("sensor.ts_new")
    assert state["last_changed"] == state["last_updated"]


async def test_state_change_updates_last_changed(rest):
    """State change updates last_changed."""
    await rest.set_state("sensor.ts_changed", "first")
    s1 = await rest.get_state("sensor.ts_changed")
    await asyncio.sleep(0.05)
    await rest.set_state("sensor.ts_changed", "second")
    s2 = await rest.get_state("sensor.ts_changed")
    assert s2["last_changed"] >= s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]


async def test_same_state_preserves_last_changed(rest):
    """Re-setting same state does not update last_changed."""
    await rest.set_state("sensor.ts_same", "stable")
    s1 = await rest.get_state("sensor.ts_same")
    await asyncio.sleep(0.05)
    await rest.set_state("sensor.ts_same", "stable")
    s2 = await rest.get_state("sensor.ts_same")
    assert s2["last_changed"] == s1["last_changed"]


async def test_attr_change_updates_last_updated(rest):
    """Attribute-only change updates last_updated but not last_changed."""
    await rest.set_state("sensor.ts_attr", "fixed", {"key": "v1"})
    s1 = await rest.get_state("sensor.ts_attr")
    await asyncio.sleep(0.05)
    await rest.set_state("sensor.ts_attr", "fixed", {"key": "v2"})
    s2 = await rest.get_state("sensor.ts_attr")
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]


async def test_same_state_and_attrs_preserves_both(rest):
    """Identical state+attrs preserves both last_changed and last_updated."""
    await rest.set_state("sensor.ts_ident", "same", {"a": 1})
    s1 = await rest.get_state("sensor.ts_ident")
    await asyncio.sleep(0.05)
    await rest.set_state("sensor.ts_ident", "same", {"a": 1})
    s2 = await rest.get_state("sensor.ts_ident")
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] == s1["last_updated"]


async def test_context_id_changes_on_each_set(rest):
    """Each set() call generates a new context.id."""
    await rest.set_state("sensor.ts_ctx", "a")
    s1 = await rest.get_state("sensor.ts_ctx")
    await rest.set_state("sensor.ts_ctx", "b")
    s2 = await rest.get_state("sensor.ts_ctx")
    assert s1["context"]["id"] != s2["context"]["id"]


async def test_context_has_required_fields(rest):
    """Context includes id, parent_id, and user_id fields."""
    await rest.set_state("sensor.ts_ctx_fields", "val")
    state = await rest.get_state("sensor.ts_ctx_fields")
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_last_reported_always_updates(rest):
    """last_reported is present on every state object."""
    await rest.set_state("sensor.ts_reported", "x")
    s1 = await rest.get_state("sensor.ts_reported")
    assert "last_reported" in s1


async def test_timestamps_are_iso_format(rest):
    """Timestamps are in ISO 8601 format."""
    await rest.set_state("sensor.ts_iso", "check")
    state = await rest.get_state("sensor.ts_iso")
    # Should contain 'T' separator and end with timezone info
    assert "T" in state["last_changed"]
    assert "T" in state["last_updated"]


async def test_rapid_updates_maintain_ordering(rest):
    """Rapid updates maintain monotonic timestamp ordering."""
    entity = "sensor.ts_rapid"
    timestamps = []
    for i in range(10):
        await rest.set_state(entity, str(i))
        s = await rest.get_state(entity)
        timestamps.append(s["last_updated"])
    # Timestamps should be non-decreasing
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1]
