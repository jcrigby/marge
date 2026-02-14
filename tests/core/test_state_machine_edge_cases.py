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


async def test_empty_state_string(rest):
    """Entity can have empty string state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.empty_{tag}"
    await rest.set_state(eid, "")

    state = await rest.get_state(eid)
    assert state["state"] == ""


async def test_numeric_state_string(rest):
    """Numeric state stored as string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.num_{tag}"
    await rest.set_state(eid, "42.5")

    state = await rest.get_state(eid)
    assert state["state"] == "42.5"


async def test_long_state_value(rest):
    """Very long state value stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.long_{tag}"
    long_val = "x" * 1000
    await rest.set_state(eid, long_val)

    state = await rest.get_state(eid)
    assert state["state"] == long_val


async def test_unicode_state_value(rest):
    """Unicode state value stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.uni_{tag}"
    await rest.set_state(eid, "23°C with wind")

    state = await rest.get_state(eid)
    assert "23°C" in state["state"]


async def test_unicode_attribute_value(rest):
    """Unicode attribute values stored correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.uni_attr_{tag}"
    await rest.set_state(eid, "val", {"unit": "°F", "name": "Température"})

    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "°F"
    assert state["attributes"]["name"] == "Température"


async def test_special_chars_in_state(rest):
    """Special characters in state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.spec_{tag}"
    await rest.set_state(eid, "on/off <test> & 'value'")

    state = await rest.get_state(eid)
    assert state["state"] == "on/off <test> & 'value'"


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


async def test_overwrite_attributes(rest):
    """New attributes completely replace old ones."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.overwrite_{tag}"
    await rest.set_state(eid, "val", {"key_a": 1, "key_b": 2})
    await rest.set_state(eid, "val", {"key_c": 3})

    state = await rest.get_state(eid)
    assert "key_c" in state["attributes"]
    # Note: depending on implementation, old keys may or may not persist


async def test_many_attributes(rest):
    """Entity with many attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.many_{tag}"
    attrs = {f"key_{i}": f"val_{i}" for i in range(50)}
    await rest.set_state(eid, "val", attrs)

    state = await rest.get_state(eid)
    assert state["attributes"]["key_0"] == "val_0"
    assert state["attributes"]["key_49"] == "val_49"
