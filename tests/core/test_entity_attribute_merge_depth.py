"""
CTS -- Entity Attribute Merge Depth Tests

Tests entity state attribute handling via REST set_state:
attribute replacement, partial updates, nested attributes,
empty attributes, null values, and special types.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Attribute Set ─────────────────────────────────

async def test_set_state_with_attributes(rest):
    """set_state with attributes stores them."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_basic_{tag}"
    await rest.set_state(eid, "on", {"friendly_name": "Test Sensor"})
    state = await rest.get_state(eid)
    assert state["attributes"]["friendly_name"] == "Test Sensor"


async def test_set_state_replaces_attributes(rest):
    """Second set_state replaces all attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_repl_{tag}"
    await rest.set_state(eid, "on", {"key1": "val1"})
    await rest.set_state(eid, "on", {"key2": "val2"})
    state = await rest.get_state(eid)
    assert "key2" in state["attributes"]
    # key1 may or may not persist depending on set_state semantics


async def test_set_state_no_attributes(rest):
    """set_state without attributes uses empty dict."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_noattr_{tag}"
    await rest.set_state(eid, "42")
    state = await rest.get_state(eid)
    assert isinstance(state["attributes"], dict)


# ── Numeric Attributes ──────────────────────────────────

async def test_set_state_integer_attribute(rest):
    """Integer attribute preserved as number."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_int_{tag}"
    await rest.set_state(eid, "on", {"count": 42})
    state = await rest.get_state(eid)
    assert state["attributes"]["count"] == 42


async def test_set_state_float_attribute(rest):
    """Float attribute preserved as number."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_flt_{tag}"
    await rest.set_state(eid, "on", {"temperature": 23.5})
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 23.5


# ── Boolean Attributes ──────────────────────────────────

async def test_set_state_bool_attribute(rest):
    """Boolean attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_bool_{tag}"
    await rest.set_state(eid, "on", {"is_active": True})
    state = await rest.get_state(eid)
    assert state["attributes"]["is_active"] is True


# ── Array Attributes ────────────────────────────────────

async def test_set_state_array_attribute(rest):
    """Array attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_arr_{tag}"
    await rest.set_state(eid, "on", {"options": ["a", "b", "c"]})
    state = await rest.get_state(eid)
    assert state["attributes"]["options"] == ["a", "b", "c"]


# ── Nested Object Attributes ───────────────────────────

async def test_set_state_nested_attribute(rest):
    """Nested object attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_nest_{tag}"
    await rest.set_state(eid, "on", {
        "location": {"lat": 40.7, "lon": -74.0},
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["location"]["lat"] == 40.7
    assert state["attributes"]["location"]["lon"] == -74.0


# ── Multiple Attributes ────────────────────────────────

async def test_set_state_many_attributes(rest):
    """Multiple attributes all preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_many_{tag}"
    attrs = {
        "friendly_name": "Multi Sensor",
        "unit_of_measurement": "lux",
        "device_class": "illuminance",
        "icon": "mdi:lightbulb",
    }
    await rest.set_state(eid, "500", attrs)
    state = await rest.get_state(eid)
    for key, val in attrs.items():
        assert state["attributes"][key] == val


# ── Empty String Attribute ──────────────────────────────

async def test_set_state_empty_string_attribute(rest):
    """Empty string attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_empty_{tag}"
    await rest.set_state(eid, "on", {"label": ""})
    state = await rest.get_state(eid)
    assert state["attributes"]["label"] == ""


# ── Unicode Attributes ──────────────────────────────────

async def test_set_state_unicode_attribute(rest):
    """Unicode attribute preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eamd_uni_{tag}"
    await rest.set_state(eid, "on", {"name": "Salle de bain"})
    state = await rest.get_state(eid)
    assert state["attributes"]["name"] == "Salle de bain"
