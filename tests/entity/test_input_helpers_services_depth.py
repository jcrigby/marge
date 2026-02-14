"""
CTS -- Input Helper Service Depth Tests

Tests input helper domain services: input_boolean (turn_on, turn_off,
toggle), input_number (set_value), input_text (set_value),
input_select (select_option), counter (increment, decrement, reset),
number (set_value), select (select_option).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Input Boolean ────────────────────────────────────────

async def test_input_boolean_turn_on(rest):
    """input_boolean.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ihsd_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("input_boolean", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ihsd_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("input_boolean", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_input_boolean_toggle_on_to_off(rest):
    """input_boolean.toggle from on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ihsd_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_input_boolean_toggle_off_to_on(rest):
    """input_boolean.toggle from off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ihsd_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Input Number ─────────────────────────────────────────

async def test_input_number_set_value(rest):
    """input_number.set_value sets state to the value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.ihsd_num_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("input_number", "set_value", {
        "entity_id": eid, "value": 42,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "42"


async def test_input_number_set_float(rest):
    """input_number.set_value with float."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_number.ihsd_flt_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("input_number", "set_value", {
        "entity_id": eid, "value": 3.14,
    })
    state = await rest.get_state(eid)
    assert "3.14" in state["state"]


# ── Input Text ───────────────────────────────────────────

async def test_input_text_set_value(rest):
    """input_text.set_value sets state to the text."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.ihsd_txt_{tag}"
    await rest.set_state(eid, "")
    await rest.call_service("input_text", "set_value", {
        "entity_id": eid, "value": "hello world",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "hello world"


async def test_input_text_set_empty(rest):
    """input_text.set_value with empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_text.ihsd_empty_{tag}"
    await rest.set_state(eid, "something")
    await rest.call_service("input_text", "set_value", {
        "entity_id": eid, "value": "",
    })
    state = await rest.get_state(eid)
    assert state["state"] == ""


# ── Input Select ─────────────────────────────────────────

async def test_input_select_option(rest):
    """input_select.select_option sets state to the option."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_select.ihsd_sel_{tag}"
    await rest.set_state(eid, "option_a")
    await rest.call_service("input_select", "select_option", {
        "entity_id": eid, "option": "option_b",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "option_b"


# ── Counter ──────────────────────────────────────────────

async def test_counter_increment(rest):
    """counter.increment increments counter state by 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ihsd_inc_{tag}"
    await rest.set_state(eid, "5")
    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "6"


async def test_counter_decrement(rest):
    """counter.decrement decrements counter state by 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ihsd_dec_{tag}"
    await rest.set_state(eid, "5")
    await rest.call_service("counter", "decrement", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "4"


async def test_counter_reset(rest):
    """counter.reset resets to initial attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ihsd_rst_{tag}"
    await rest.set_state(eid, "10", {"initial": 0})
    await rest.call_service("counter", "reset", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "0"


async def test_counter_increment_from_zero(rest):
    """counter.increment from 0 → 1."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ihsd_i0_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("counter", "increment", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "1"


# ── Number (Generic) ────────────────────────────────────

async def test_number_set_value(rest):
    """number.set_value sets state to the value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"number.ihsd_nval_{tag}"
    await rest.set_state(eid, "0")
    await rest.call_service("number", "set_value", {
        "entity_id": eid, "value": 75,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "75"


# ── Select (Generic) ────────────────────────────────────

async def test_select_option(rest):
    """select.select_option sets state to the option."""
    tag = uuid.uuid4().hex[:8]
    eid = f"select.ihsd_gsel_{tag}"
    await rest.set_state(eid, "mode_a")
    await rest.call_service("select", "select_option", {
        "entity_id": eid, "option": "mode_b",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "mode_b"
