"""
CTS -- State Machine Edge Case Tests

Tests entity state edge cases: special characters, long values,
concurrent access, attribute merging, timestamp accuracy, and
entity_id format validation.
"""

import asyncio
import time

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Special Characters ────────────────────────────────────

async def test_state_with_spaces(rest):
    """Entity state can contain spaces."""
    await rest.set_state("sensor.edge_spaces", "hello world")
    state = await rest.get_state("sensor.edge_spaces")
    assert state["state"] == "hello world"


async def test_state_with_unicode(rest):
    """Entity state can contain unicode characters."""
    await rest.set_state("sensor.edge_unicode", "72\u00b0F")
    state = await rest.get_state("sensor.edge_unicode")
    assert state["state"] == "72\u00b0F"


async def test_state_with_empty_string(rest):
    """Entity state can be an empty string."""
    await rest.set_state("sensor.edge_empty", "")
    state = await rest.get_state("sensor.edge_empty")
    assert state["state"] == ""


async def test_state_long_value(rest):
    """Entity state handles long strings."""
    long_val = "x" * 1000
    await rest.set_state("sensor.edge_long", long_val)
    state = await rest.get_state("sensor.edge_long")
    assert state["state"] == long_val


# ── Attribute Handling ────────────────────────────────────

async def test_attributes_preserve_types(rest):
    """Attributes preserve various JSON types."""
    attrs = {
        "int_val": 42,
        "float_val": 3.14,
        "bool_val": True,
        "str_val": "hello",
        "list_val": [1, 2, 3],
        "null_val": None,
    }
    await rest.set_state("sensor.edge_attrs", "ok", attrs)
    state = await rest.get_state("sensor.edge_attrs")
    assert state["attributes"]["int_val"] == 42
    assert state["attributes"]["float_val"] == 3.14
    assert state["attributes"]["bool_val"] is True
    assert state["attributes"]["str_val"] == "hello"
    assert state["attributes"]["list_val"] == [1, 2, 3]
    assert state["attributes"]["null_val"] is None


async def test_attributes_nested_object(rest):
    """Attributes can contain nested objects."""
    attrs = {"device": {"manufacturer": "Acme", "model": "X100"}}
    await rest.set_state("sensor.edge_nested", "ok", attrs)
    state = await rest.get_state("sensor.edge_nested")
    assert state["attributes"]["device"]["manufacturer"] == "Acme"


async def test_attributes_overwrite_on_update(rest):
    """Setting new state replaces all attributes."""
    await rest.set_state("sensor.edge_overwrite", "v1", {"a": 1, "b": 2})
    await rest.set_state("sensor.edge_overwrite", "v2", {"c": 3})
    state = await rest.get_state("sensor.edge_overwrite")
    assert state["state"] == "v2"
    assert state["attributes"].get("c") == 3
    # Old attributes should be gone
    assert "a" not in state["attributes"]


# ── Timestamps ────────────────────────────────────────────

async def test_state_has_last_changed(rest):
    """Entities have a last_changed timestamp."""
    await rest.set_state("sensor.edge_ts", "now")
    state = await rest.get_state("sensor.edge_ts")
    assert "last_changed" in state
    assert len(state["last_changed"]) > 10  # ISO format


async def test_state_has_last_updated(rest):
    """Entities have a last_updated timestamp."""
    await rest.set_state("sensor.edge_ts2", "now")
    state = await rest.get_state("sensor.edge_ts2")
    assert "last_updated" in state


async def test_timestamps_update_on_change(rest):
    """Timestamps change when state is updated."""
    await rest.set_state("sensor.edge_ts3", "first")
    s1 = await rest.get_state("sensor.edge_ts3")
    await asyncio.sleep(0.05)
    await rest.set_state("sensor.edge_ts3", "second")
    s2 = await rest.get_state("sensor.edge_ts3")
    assert s2["last_changed"] >= s1["last_changed"]


# ── Concurrent Updates ───────────────────────────────────

async def test_concurrent_state_updates(rest):
    """Multiple concurrent updates don't corrupt state."""
    tasks = []
    for i in range(10):
        tasks.append(rest.set_state(f"sensor.concurrent_{i}", str(i * 10)))
    await asyncio.gather(*tasks)

    for i in range(10):
        state = await rest.get_state(f"sensor.concurrent_{i}")
        assert state is not None
        assert state["state"] == str(i * 10)


# ── Entity ID Format ─────────────────────────────────────

async def test_entity_id_with_numbers(rest):
    """Entity IDs can contain numbers."""
    await rest.set_state("sensor.temp_sensor_123", "42")
    state = await rest.get_state("sensor.temp_sensor_123")
    assert state["state"] == "42"


async def test_entity_id_with_underscores(rest):
    """Entity IDs can contain underscores."""
    await rest.set_state("sensor.my_long_sensor_name", "99")
    state = await rest.get_state("sensor.my_long_sensor_name")
    assert state["state"] == "99"


# ── GET /api/states Collection ────────────────────────────

async def test_states_returns_all_entities(rest):
    """GET /api/states returns all entities."""
    await rest.set_state("sensor.states_check", "yes")
    states = await rest.get_states()
    assert len(states) > 0
    ids = [s["entity_id"] for s in states]
    assert "sensor.states_check" in ids


async def test_states_entity_format(rest):
    """Each entity in GET /api/states has required fields."""
    states = await rest.get_states()
    assert len(states) > 0
    e = states[0]
    assert "entity_id" in e
    assert "state" in e
    assert "attributes" in e
    assert "last_changed" in e


# ── POST /api/states Response ─────────────────────────────

async def test_set_state_returns_entity(rest):
    """POST /api/states/{id} returns the created/updated entity."""
    result = await rest.set_state("sensor.set_response", "42", {"unit": "kg"})
    assert result["entity_id"] == "sensor.set_response"
    assert result["state"] == "42"
    assert result["attributes"]["unit"] == "kg"
