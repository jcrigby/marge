"""
CTS -- State Attribute Type Preservation Depth Tests

Tests that different JSON value types in attributes are correctly
preserved through set/get cycles: numbers, booleans, nulls, arrays,
nested objects, and mixed-type attribute maps.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Numeric Types ─────────────────────────────────────────

async def test_integer_attribute(rest):
    """Integer attribute values are preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_int_{tag}"
    await rest.set_state(eid, "1", {"count": 42})
    state = await rest.get_state(eid)
    assert state["attributes"]["count"] == 42


async def test_float_attribute(rest):
    """Float attribute values are preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_float_{tag}"
    await rest.set_state(eid, "1", {"temperature": 72.5})
    state = await rest.get_state(eid)
    assert abs(state["attributes"]["temperature"] - 72.5) < 0.01


async def test_zero_attribute(rest):
    """Zero numeric attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_zero_{tag}"
    await rest.set_state(eid, "1", {"level": 0})
    state = await rest.get_state(eid)
    assert state["attributes"]["level"] == 0


async def test_negative_attribute(rest):
    """Negative numeric attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_neg_{tag}"
    await rest.set_state(eid, "1", {"offset": -15.3})
    state = await rest.get_state(eid)
    assert abs(state["attributes"]["offset"] - (-15.3)) < 0.01


# ── Boolean Types ─────────────────────────────────────────

async def test_true_attribute(rest):
    """True boolean attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_true_{tag}"
    await rest.set_state(eid, "1", {"active": True})
    state = await rest.get_state(eid)
    assert state["attributes"]["active"] is True


async def test_false_attribute(rest):
    """False boolean attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_false_{tag}"
    await rest.set_state(eid, "1", {"active": False})
    state = await rest.get_state(eid)
    assert state["attributes"]["active"] is False


# ── Null Type ─────────────────────────────────────────────

async def test_null_attribute(rest):
    """Null attribute value preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_null_{tag}"
    await rest.set_state(eid, "1", {"optional": None})
    state = await rest.get_state(eid)
    assert state["attributes"]["optional"] is None


# ── Array Types ───────────────────────────────────────────

async def test_string_array_attribute(rest):
    """String array attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_sarr_{tag}"
    await rest.set_state(eid, "1", {"options": ["a", "b", "c"]})
    state = await rest.get_state(eid)
    assert state["attributes"]["options"] == ["a", "b", "c"]


async def test_numeric_array_attribute(rest):
    """Numeric array attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_narr_{tag}"
    await rest.set_state(eid, "1", {"values": [1, 2.5, 3]})
    state = await rest.get_state(eid)
    assert state["attributes"]["values"] == [1, 2.5, 3]


async def test_empty_array_attribute(rest):
    """Empty array attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_earr_{tag}"
    await rest.set_state(eid, "1", {"items": []})
    state = await rest.get_state(eid)
    assert state["attributes"]["items"] == []


# ── Nested Object Types ──────────────────────────────────

async def test_nested_object_attribute(rest):
    """Nested object attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_nobj_{tag}"
    await rest.set_state(eid, "1", {
        "config": {"mode": "auto", "level": 5},
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["config"]["mode"] == "auto"
    assert state["attributes"]["config"]["level"] == 5


async def test_deeply_nested_attribute(rest):
    """Deeply nested attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_deep_{tag}"
    await rest.set_state(eid, "1", {
        "a": {"b": {"c": {"d": "deep_value"}}},
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["a"]["b"]["c"]["d"] == "deep_value"


# ── Mixed Types ───────────────────────────────────────────

async def test_mixed_type_attributes(rest):
    """Multiple attribute types in one entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_mix_{tag}"
    attrs = {
        "str_val": "hello",
        "int_val": 42,
        "float_val": 3.14,
        "bool_val": True,
        "null_val": None,
        "arr_val": [1, "two"],
        "obj_val": {"key": "val"},
    }
    await rest.set_state(eid, "1", attrs)
    state = await rest.get_state(eid)

    assert state["attributes"]["str_val"] == "hello"
    assert state["attributes"]["int_val"] == 42
    assert abs(state["attributes"]["float_val"] - 3.14) < 0.01
    assert state["attributes"]["bool_val"] is True
    assert state["attributes"]["null_val"] is None
    assert state["attributes"]["arr_val"] == [1, "two"]
    assert state["attributes"]["obj_val"]["key"] == "val"


async def test_empty_string_attribute(rest):
    """Empty string attribute preserved (not null)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sat_estr_{tag}"
    await rest.set_state(eid, "1", {"name": ""})
    state = await rest.get_state(eid)
    assert state["attributes"]["name"] == ""
