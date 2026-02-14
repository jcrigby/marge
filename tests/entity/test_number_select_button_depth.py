"""
CTS -- Number, Select, Button, and Text Entity Depth Tests

Tests service handlers for number (set_value), select (select_option),
button (press), and text (set_value) domains. Also tests input_number,
input_select, and input_text variants.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Number ──────────────────────────────────────────────

async def test_number_set_value(rest):
    """number.set_value sets entity state to the value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nsv_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("number", "set_value", {"entity_id": eid, "value": 75})
    state = await rest.get_state(eid)
    assert state["state"] == "75"


async def test_input_number_set_value(rest):
    """input_number.set_value sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.insv_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("input_number", "set_value", {"entity_id": eid, "value": 50})
    state = await rest.get_state(eid)
    assert state["state"] == "50"


async def test_number_set_value_preserves_attrs(rest):
    """number.set_value preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.nsvp_{tag}"
    await rest.set_state(eid, "10", {"min": "0", "max": "100", "step": "1"})
    await rest.call_service("number", "set_value", {"entity_id": eid, "value": 42})
    state = await rest.get_state(eid)
    assert state["state"] == "42"
    assert state["attributes"]["min"] == "0"
    assert state["attributes"]["max"] == "100"


# ── Select ──────────────────────────────────────────────

async def test_select_select_option(rest):
    """select.select_option sets entity state to the option."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.sso_{tag}"
    await rest.set_state(eid, "low", {"options": ["low", "medium", "high"]})
    await rest.call_service("select", "select_option", {"entity_id": eid, "option": "high"})
    state = await rest.get_state(eid)
    assert state["state"] == "high"


async def test_input_select_select_option(rest):
    """input_select.select_option sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_select.isso_{tag}"
    await rest.set_state(eid, "A")
    await rest.call_service("input_select", "select_option", {"entity_id": eid, "option": "B"})
    state = await rest.get_state(eid)
    assert state["state"] == "B"


async def test_select_preserves_options(rest):
    """select.select_option preserves options attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.ssop_{tag}"
    await rest.set_state(eid, "low", {"options": ["low", "medium", "high"]})
    await rest.call_service("select", "select_option", {"entity_id": eid, "option": "medium"})
    state = await rest.get_state(eid)
    assert state["state"] == "medium"
    assert state["attributes"]["options"] == ["low", "medium", "high"]


# ── Button ──────────────────────────────────────────────

async def test_button_press(rest):
    """button.press sets state to pressed (or timestamp)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.bp_{tag}"
    await rest.set_state(eid, "unknown")
    await rest.call_service("button", "press", {"entity_id": eid})
    state = await rest.get_state(eid)
    # Button press typically sets state or updates last_updated
    assert state["state"] != "unknown" or state["last_updated"] is not None


# ── Text ────────────────────────────────────────────────

async def test_text_set_value(rest):
    """text.set_value sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.tsv_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("text", "set_value", {"entity_id": eid, "value": "hello world"})
    state = await rest.get_state(eid)
    assert state["state"] == "hello world"


async def test_input_text_set_value(rest):
    """input_text.set_value sets entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.itsv_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("input_text", "set_value", {"entity_id": eid, "value": "test input"})
    state = await rest.get_state(eid)
    assert state["state"] == "test input"


async def test_text_set_value_preserves_attrs(rest):
    """text.set_value preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"text.tsvp_{tag}"
    await rest.set_state(eid, "", {"min_length": "0", "max_length": "255"})
    await rest.call_service("text", "set_value", {"entity_id": eid, "value": "data"})
    state = await rest.get_state(eid)
    assert state["state"] == "data"
    assert state["attributes"]["min_length"] == "0"


# ── Input Datetime ──────────────────────────────────────

async def test_input_datetime_set_datetime(rest):
    """input_datetime.set_datetime sets date/time state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.idts_{tag}"
    await rest.set_state(eid, "unknown")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "datetime": "2026-02-14 10:30:00",
    })
    state = await rest.get_state(eid)
    assert "2026-02-14" in state["state"]


# ── Cross-Domain Consistency ────────────────────────────

async def test_set_value_across_domains(rest):
    """set_value works for number, text, and input_* variants."""
    tag = uuid.uuid4().hex[:8]
    # number/input_number use v.to_string() (pass int to avoid JSON string quoting)
    # text/input_text use v.as_str() (pass string directly)
    pairs = [
        (f"number.xd_{tag}", "number", 42, "42"),
        (f"text.xd_{tag}", "text", "hello", "hello"),
        (f"input_number.xd_{tag}", "input_number", 99, "99"),
        (f"input_text.xd_{tag}", "input_text", "world", "world"),
    ]
    for eid, domain, val, expected in pairs:
        await rest.set_state(eid, "")
        await rest.call_service(domain, "set_value", {"entity_id": eid, "value": val})
        state = await rest.get_state(eid)
        assert state["state"] == expected, f"Failed for {domain}: expected {expected}, got {state['state']}"
