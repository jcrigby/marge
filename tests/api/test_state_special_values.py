"""
CTS -- State Special Value and Edge Case Tests

Tests state machine behavior with special characters, unicode,
long values, numeric types, empty/null scenarios, and attribute
edge cases.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Unicode States ───────────────────────────────────────

async def test_state_unicode_value(rest):
    """State with unicode characters."""
    await rest.set_state("sensor.ssv_unicode", "23.5\u00b0C")
    state = await rest.get_state("sensor.ssv_unicode")
    assert state["state"] == "23.5\u00b0C"


async def test_state_unicode_attribute(rest):
    """Attribute with unicode characters."""
    await rest.set_state("sensor.ssv_uattr", "ok", {"unit": "\u00b0F"})
    state = await rest.get_state("sensor.ssv_uattr")
    assert state["attributes"]["unit"] == "\u00b0F"


async def test_state_cjk_characters(rest):
    """State with CJK characters."""
    await rest.set_state("sensor.ssv_cjk", "\u6e29\u5ea6")
    state = await rest.get_state("sensor.ssv_cjk")
    assert state["state"] == "\u6e29\u5ea6"


# ── Special Characters ──────────────────────────────────

async def test_state_with_quotes(rest):
    """State value containing quotes."""
    await rest.set_state("sensor.ssv_quotes", 'He said "hello"')
    state = await rest.get_state("sensor.ssv_quotes")
    assert state["state"] == 'He said "hello"'


async def test_state_with_newlines(rest):
    """State value containing newlines."""
    await rest.set_state("sensor.ssv_newline", "line1\nline2")
    state = await rest.get_state("sensor.ssv_newline")
    assert state["state"] == "line1\nline2"


async def test_state_with_backslashes(rest):
    """State value containing backslashes."""
    await rest.set_state("sensor.ssv_backslash", "path\\to\\file")
    state = await rest.get_state("sensor.ssv_backslash")
    assert state["state"] == "path\\to\\file"


async def test_state_with_angle_brackets(rest):
    """State value containing HTML-like characters."""
    await rest.set_state("sensor.ssv_html", "<b>bold</b>")
    state = await rest.get_state("sensor.ssv_html")
    assert state["state"] == "<b>bold</b>"


# ── Long Values ─────────────────────────────────────────

async def test_state_long_string(rest):
    """State with very long string value."""
    long_val = "x" * 10000
    await rest.set_state("sensor.ssv_long", long_val)
    state = await rest.get_state("sensor.ssv_long")
    assert state["state"] == long_val


async def test_state_many_attributes(rest):
    """State with many attributes."""
    attrs = {f"attr_{i}": i for i in range(50)}
    await rest.set_state("sensor.ssv_many_attrs", "ok", attrs)
    state = await rest.get_state("sensor.ssv_many_attrs")
    assert len(state["attributes"]) >= 50


# ── Numeric Types ────────────────────────────────────────

async def test_state_integer_preserved(rest):
    """Integer state preserved as string."""
    await rest.set_state("sensor.ssv_int", "42")
    state = await rest.get_state("sensor.ssv_int")
    assert state["state"] == "42"


async def test_state_float_preserved(rest):
    """Float state preserved as string."""
    await rest.set_state("sensor.ssv_float", "3.14159")
    state = await rest.get_state("sensor.ssv_float")
    assert state["state"] == "3.14159"


async def test_state_negative_number(rest):
    """Negative number state preserved."""
    await rest.set_state("sensor.ssv_neg", "-273.15")
    state = await rest.get_state("sensor.ssv_neg")
    assert state["state"] == "-273.15"


async def test_state_scientific_notation(rest):
    """Scientific notation state preserved."""
    await rest.set_state("sensor.ssv_sci", "1.23e10")
    state = await rest.get_state("sensor.ssv_sci")
    assert state["state"] == "1.23e10"


async def test_attribute_integer_value(rest):
    """Integer attribute value preserved."""
    await rest.set_state("sensor.ssv_attr_int", "ok", {"count": 42})
    state = await rest.get_state("sensor.ssv_attr_int")
    assert state["attributes"]["count"] == 42


async def test_attribute_float_value(rest):
    """Float attribute value preserved."""
    await rest.set_state("sensor.ssv_attr_float", "ok", {"temp": 72.5})
    state = await rest.get_state("sensor.ssv_attr_float")
    assert state["attributes"]["temp"] == 72.5


async def test_attribute_boolean_value(rest):
    """Boolean attribute value preserved."""
    await rest.set_state("sensor.ssv_attr_bool", "ok", {"active": True})
    state = await rest.get_state("sensor.ssv_attr_bool")
    assert state["attributes"]["active"] is True


async def test_attribute_null_value(rest):
    """Null attribute value preserved."""
    await rest.set_state("sensor.ssv_attr_null", "ok", {"cleared": None})
    state = await rest.get_state("sensor.ssv_attr_null")
    assert state["attributes"]["cleared"] is None


async def test_attribute_nested_object(rest):
    """Nested object attribute preserved."""
    nested = {"location": {"lat": 40.39, "lon": -111.85}}
    await rest.set_state("sensor.ssv_attr_nested", "ok", nested)
    state = await rest.get_state("sensor.ssv_attr_nested")
    assert state["attributes"]["location"]["lat"] == 40.39


async def test_attribute_array_value(rest):
    """Array attribute value preserved."""
    await rest.set_state("sensor.ssv_attr_arr", "ok", {"colors": [255, 128, 0]})
    state = await rest.get_state("sensor.ssv_attr_arr")
    assert state["attributes"]["colors"] == [255, 128, 0]


# ── Empty/Boundary States ───────────────────────────────

async def test_state_empty_string(rest):
    """Empty string state is valid."""
    await rest.set_state("sensor.ssv_empty", "")
    state = await rest.get_state("sensor.ssv_empty")
    assert state["state"] == ""


async def test_state_whitespace_only(rest):
    """Whitespace-only state preserved."""
    await rest.set_state("sensor.ssv_ws", "   ")
    state = await rest.get_state("sensor.ssv_ws")
    assert state["state"] == "   "


async def test_state_single_char(rest):
    """Single character state works."""
    await rest.set_state("sensor.ssv_single", "x")
    state = await rest.get_state("sensor.ssv_single")
    assert state["state"] == "x"


async def test_state_zero_string(rest):
    """Zero as string state works."""
    await rest.set_state("sensor.ssv_zero", "0")
    state = await rest.get_state("sensor.ssv_zero")
    assert state["state"] == "0"


# ── State Overwrite Semantics ───────────────────────────

async def test_state_overwrite_preserves_entity_id(rest):
    """Overwriting state preserves entity_id in response."""
    await rest.set_state("sensor.ssv_overwrite", "first")
    state = await rest.set_state("sensor.ssv_overwrite", "second")
    assert state["entity_id"] == "sensor.ssv_overwrite"
    assert state["state"] == "second"


async def test_state_overwrite_replaces_attributes(rest):
    """New attributes replace old ones on state set."""
    await rest.set_state("sensor.ssv_replace", "v1", {"a": 1, "b": 2})
    await rest.set_state("sensor.ssv_replace", "v2", {"c": 3})
    state = await rest.get_state("sensor.ssv_replace")
    assert state["state"] == "v2"
    assert "c" in state["attributes"]


async def test_state_timestamps_change_on_update(rest):
    """last_changed and last_updated change on state update."""
    await rest.set_state("sensor.ssv_ts", "first")
    s1 = await rest.get_state("sensor.ssv_ts")

    import asyncio
    await asyncio.sleep(0.1)

    await rest.set_state("sensor.ssv_ts", "second")
    s2 = await rest.get_state("sensor.ssv_ts")

    assert s2["last_changed"] >= s1["last_changed"]
    assert s2["last_updated"] >= s1["last_updated"]
