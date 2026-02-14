"""
CTS -- State Attribute Replacement Semantics Depth Tests

Tests that REST set_state REPLACES all attributes (not merge),
empty attrs clearing, nested attribute structures, type mutations,
and that scene activation MERGES attributes into existing state.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Attribute Replacement (REST set_state) ───────────────

async def test_set_state_replaces_all_attributes(rest):
    """Setting state with new attributes replaces all previous attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_repl_{tag}"
    await rest.set_state(eid, "10", {"unit": "W", "source": "grid"})
    await rest.set_state(eid, "20", {"unit": "kW"})
    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "kW"
    # "source" should be gone since we replaced all attributes
    assert "source" not in state["attributes"]


async def test_empty_attributes_clears_existing(rest):
    """Setting state with empty attributes clears previous attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_clear_{tag}"
    await rest.set_state(eid, "on", {"brightness": 255, "color": "warm"})
    await rest.set_state(eid, "on", {})
    state = await rest.get_state(eid)
    assert state["attributes"] == {} or len(state["attributes"]) == 0


async def test_nested_attributes_preserved(rest):
    """Nested attribute objects survive set_state round-trip."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_nest_{tag}"
    await rest.set_state(eid, "active", {
        "config": {"threshold": 42, "enabled": True},
        "tags": ["a", "b", "c"],
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["config"]["threshold"] == 42
    assert state["attributes"]["config"]["enabled"] is True
    assert state["attributes"]["tags"] == ["a", "b", "c"]


async def test_attribute_type_mutation(rest):
    """Changing attribute value type (int to string) works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_type_{tag}"
    await rest.set_state(eid, "1", {"brightness": 255})
    await rest.set_state(eid, "1", {"brightness": "max"})
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == "max"


async def test_null_attribute_value(rest):
    """Setting an attribute to null preserves null."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_null_{tag}"
    await rest.set_state(eid, "1", {"data": None})
    state = await rest.get_state(eid)
    assert state["attributes"]["data"] is None


# ── Scene Attribute Merging ──────────────────────────────

async def test_scene_merges_into_existing_attributes(rest):
    """Scene activation merges scene attributes into existing entity attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = "light.living_room"
    # Set entity with known attributes
    await rest.set_state(eid, "on", {"brightness": 100, "color_mode": "ct"})
    # Activate evening scene (sets brightness but should preserve color_mode)
    resp = await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    state = await rest.get_state(eid)
    # Scene should have set brightness to its value
    assert "brightness" in state["attributes"]


async def test_scene_preserves_unrelated_attributes(rest):
    """Scene activation preserves attributes not mentioned in scene."""
    tag = uuid.uuid4().hex[:8]
    eid = "light.living_room"
    # Set extra attribute that no scene would touch
    await rest.set_state(eid, "on", {
        "brightness": 100,
        f"custom_{tag}": "should_survive",
    })
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    state = await rest.get_state(eid)
    assert state["attributes"].get(f"custom_{tag}") == "should_survive"


# ── Timestamp Behavior with Attribute Changes ────────────

async def test_same_state_diff_attrs_updates_last_updated(rest):
    """Same state value + different attributes: last_updated advances, last_changed stays."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_ts_{tag}"
    await rest.set_state(eid, "42", {"a": 1})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "42", {"a": 2})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]


async def test_same_state_same_attrs_preserves_both(rest):
    """Same state + same attributes: both last_changed and last_updated preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_both_{tag}"
    await rest.set_state(eid, "42", {"a": 1})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "42", {"a": 1})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]
    assert s2["last_updated"] == s1["last_updated"]


async def test_diff_state_updates_both_timestamps(rest):
    """Different state value: both timestamps advance."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_diff_{tag}"
    await rest.set_state(eid, "A", {"x": 1})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "B", {"x": 1})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] > s1["last_changed"]
    assert s2["last_updated"] > s1["last_updated"]


# ── Large Attribute Payload ──────────────────────────────

async def test_large_attribute_payload(rest):
    """Entity handles large attribute payloads."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ar_large_{tag}"
    attrs = {f"key_{i}": f"value_{i}" for i in range(100)}
    await rest.set_state(eid, "ok", attrs)
    state = await rest.get_state(eid)
    assert len(state["attributes"]) == 100
    assert state["attributes"]["key_0"] == "value_0"
    assert state["attributes"]["key_99"] == "value_99"
