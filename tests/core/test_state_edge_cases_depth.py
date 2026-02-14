"""
CTS -- State Machine Edge Cases Depth Tests

Tests boundary conditions: empty state strings, large attribute values,
unicode entity IDs, state value types, and context generation.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_empty_state_value(rest):
    """Entity with empty string state."""
    await rest.set_state("sensor.edge_empty", "")
    state = await rest.get_state("sensor.edge_empty")
    assert state["state"] == ""


async def test_state_with_unicode(rest):
    """State value with unicode characters."""
    await rest.set_state("sensor.edge_unicode", "温度: 22°C")
    state = await rest.get_state("sensor.edge_unicode")
    assert state["state"] == "温度: 22°C"


async def test_attribute_with_unicode(rest):
    """Attribute with unicode values."""
    await rest.set_state("sensor.edge_unicode_attr", "ok", {
        "label": "Température",
    })
    state = await rest.get_state("sensor.edge_unicode_attr")
    assert state["attributes"]["label"] == "Température"


async def test_large_attribute_value(rest):
    """Large attribute value (1KB+ string)."""
    large_val = "x" * 2000
    await rest.set_state("sensor.edge_large", "ok", {"big": large_val})
    state = await rest.get_state("sensor.edge_large")
    assert len(state["attributes"]["big"]) == 2000


async def test_many_attributes(rest):
    """Entity with many attributes."""
    attrs = {f"key_{i}": f"val_{i}" for i in range(50)}
    await rest.set_state("sensor.edge_many_attrs", "ok", attrs)
    state = await rest.get_state("sensor.edge_many_attrs")
    assert len(state["attributes"]) >= 50


async def test_numeric_state_stays_string(rest):
    """Numeric-like state values stay as strings."""
    await rest.set_state("sensor.edge_numstr", "3.14159")
    state = await rest.get_state("sensor.edge_numstr")
    assert isinstance(state["state"], str)
    assert state["state"] == "3.14159"


async def test_boolean_like_state(rest):
    """Boolean-like state values stay as strings."""
    await rest.set_state("sensor.edge_bool", "true")
    state = await rest.get_state("sensor.edge_bool")
    assert isinstance(state["state"], str)
    assert state["state"] == "true"


async def test_context_has_id(rest):
    """State context has id field."""
    await rest.set_state("sensor.edge_ctx", "val")
    state = await rest.get_state("sensor.edge_ctx")
    assert "context" in state
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_context_changes_on_update(rest):
    """Context id changes on each state update."""
    await rest.set_state("sensor.edge_ctx2", "a")
    s1 = await rest.get_state("sensor.edge_ctx2")
    ctx1 = s1["context"]["id"]

    await rest.set_state("sensor.edge_ctx2", "b")
    s2 = await rest.get_state("sensor.edge_ctx2")
    ctx2 = s2["context"]["id"]

    assert ctx1 != ctx2


async def test_last_updated_iso_format(rest):
    """last_updated is ISO 8601 format."""
    await rest.set_state("sensor.edge_iso", "val")
    state = await rest.get_state("sensor.edge_iso")
    lu = state["last_updated"]
    assert "T" in lu  # ISO 8601 has T separator
    assert "20" in lu  # starts with year 20xx


async def test_set_state_returns_entity(rest):
    """POST /api/states returns the created entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.edge_ret",
        json={"state": "42", "attributes": {"unit": "kg"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "sensor.edge_ret"
    assert data["state"] == "42"
    assert data["attributes"]["unit"] == "kg"
