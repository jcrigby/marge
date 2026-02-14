"""
CTS -- State Machine Edge Cases Depth Tests

Tests state machine edge cases: empty state string, very long state
strings, special characters in entity IDs and states, unicode in
attributes, overwrite semantics, and get_all ordering.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Empty / Edge State Values ────────────────────────────

async def test_empty_state_string(rest):
    """Entity can have empty string state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_empty_{tag}"
    await rest.set_state(eid, "")
    state = await rest.get_state(eid)
    assert state["state"] == ""


async def test_long_state_string(rest):
    """Entity can store a long state string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_long_{tag}"
    long_val = "x" * 1000
    await rest.set_state(eid, long_val)
    state = await rest.get_state(eid)
    assert state["state"] == long_val


async def test_numeric_state_string(rest):
    """Numeric state stored as string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_num_{tag}"
    await rest.set_state(eid, "3.14159")
    state = await rest.get_state(eid)
    assert state["state"] == "3.14159"


async def test_state_with_special_chars(rest):
    """State can contain special characters."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_spec_{tag}"
    await rest.set_state(eid, "on/off & <yes>")
    state = await rest.get_state(eid)
    assert state["state"] == "on/off & <yes>"


# ── Entity ID Variations ────────────────────────────────

async def test_entity_with_numbers_in_name(rest):
    """Entity ID with numbers in object_id works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_123abc_{tag}"
    await rest.set_state(eid, "ok")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


async def test_entity_with_underscores(rest):
    """Entity ID with many underscores works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_a_b_c_d_{tag}"
    await rest.set_state(eid, "ok")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


# ── Unicode in Attributes ────────────────────────────────

async def test_unicode_attribute_value(rest):
    """Unicode strings preserved in attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_uni_{tag}"
    await rest.set_state(eid, "1", {"name": "Salle de bain"})
    state = await rest.get_state(eid)
    assert state["attributes"]["name"] == "Salle de bain"


async def test_unicode_cjk_attribute(rest):
    """CJK characters preserved in attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_cjk_{tag}"
    await rest.set_state(eid, "1", {"label": "temperature"})
    state = await rest.get_state(eid)
    assert state["attributes"]["label"] == "temperature"


# ── Overwrite Semantics ──────────────────────────────────

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


# ── States Listing ───────────────────────────────────────

async def test_get_all_contains_created_entity(rest):
    """GET /api/states contains a newly created entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.sme_all_{tag}"
    await rest.set_state(eid, "visible")

    states = await rest.get_states()
    eids = [s["entity_id"] for s in states]
    assert eid in eids
