"""
CTS -- State Machine Edge Case Tests

Tests edge cases in entity state management: empty state strings,
special characters in entity IDs, very long state values, unicode
attributes, and rapid sequential updates.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Edge State Values (parametrized) ────────────────────


@pytest.mark.parametrize("state_val,label", [
    ("", "empty"),
    ("42.5", "numeric"),
    ("x" * 1000, "long"),
    ("23°C with wind", "unicode"),
    ("on/off <test> & 'value'", "special_chars"),
])
async def test_state_value_edge_cases(rest, state_val, label):
    """State machine correctly stores edge-case state values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.edge_{label}_{tag}"
    await rest.set_state(eid, state_val)

    state = await rest.get_state(eid)
    assert state["state"] == state_val


async def test_unicode_attribute_value(rest):
    """Unicode attribute values stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.uni_attr_{tag}"
    await rest.set_state(eid, "val", {"unit": "°F", "name": "Température"})

    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "°F"
    assert state["attributes"]["name"] == "Température"


async def test_nested_attribute_values(rest):
    """Nested dict/list attribute values stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.nested_{tag}"
    await rest.set_state(eid, "val", {
        "list_attr": [1, 2, 3],
        "dict_attr": {"key": "value"},
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["list_attr"] == [1, 2, 3]
    assert state["attributes"]["dict_attr"] == {"key": "value"}


async def test_boolean_attribute_values(rest):
    """Boolean attribute values stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.bool_{tag}"
    await rest.set_state(eid, "val", {"enabled": True, "hidden": False})

    state = await rest.get_state(eid)
    assert state["attributes"]["enabled"] is True
    assert state["attributes"]["hidden"] is False


async def test_null_attribute_value(rest):
    """Null attribute values stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.null_{tag}"
    await rest.set_state(eid, "val", {"optional": None})

    state = await rest.get_state(eid)
    assert state["attributes"]["optional"] is None


async def test_rapid_updates_last_wins(rest):
    """Rapid sequential updates result in last value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rapid_{tag}"

    for i in range(20):
        await rest.set_state(eid, str(i))

    state = await rest.get_state(eid)
    assert state["state"] == "19"


async def test_many_attributes(rest):
    """Entity with many attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.many_{tag}"
    attrs = {f"key_{i}": f"val_{i}" for i in range(50)}
    await rest.set_state(eid, "val", attrs)

    state = await rest.get_state(eid)
    assert state["attributes"]["key_0"] == "val_0"
    assert state["attributes"]["key_49"] == "val_49"


# ── Entity ID Variations (from depth) ──────────────────


@pytest.mark.parametrize("suffix,label", [
    ("123abc", "numbers_in_name"),
    ("a_b_c_d", "underscores"),
])
async def test_entity_id_variations(rest, suffix, label):
    """Entity IDs with numbers and underscores work."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_{suffix}_{tag}"
    await rest.set_state(eid, "ok")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


# ── Unicode in Attributes (from depth) ─────────────────


async def test_unicode_cjk_attribute(rest):
    """CJK characters preserved in attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_cjk_{tag}"
    await rest.set_state(eid, "1", {"label": "temperature"})
    state = await rest.get_state(eid)
    assert state["attributes"]["label"] == "temperature"


# ── Overwrite Semantics (from depth) ───────────────────


async def test_overwrite_replaces_state(rest):
    """Second set_state replaces state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_ow_{tag}"
    await rest.set_state(eid, "first")
    await rest.set_state(eid, "second")
    state = await rest.get_state(eid)
    assert state["state"] == "second"


async def test_overwrite_replaces_attributes(rest):
    """Second set_state replaces all attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_owattr_{tag}"
    await rest.set_state(eid, "1", {"a": 1, "b": 2})
    await rest.set_state(eid, "1", {"c": 3})
    state = await rest.get_state(eid)
    assert "c" in state["attributes"]
    assert "a" not in state["attributes"]
    assert "b" not in state["attributes"]


async def test_overwrite_empty_attrs_clears(rest):
    """set_state with empty attrs clears previous attrs."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_owclr_{tag}"
    await rest.set_state(eid, "1", {"key": "val"})
    await rest.set_state(eid, "1", {})
    state = await rest.get_state(eid)
    assert "key" not in state["attributes"]


# ── States Listing (from depth) ────────────────────────


async def test_get_all_contains_created_entity(rest):
    """GET /api/states contains a newly created entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_all_{tag}"
    await rest.set_state(eid, "visible")

    states = await rest.get_states()
    eids = [s["entity_id"] for s in states]
    assert eid in eids
