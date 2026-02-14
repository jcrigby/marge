"""
CTS -- Input Helper Service Depth Tests

Tests input_boolean, input_number, input_text, input_select,
and input_datetime service handlers with various operations.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Input Boolean ────────────────────────────────────────

async def test_input_boolean_turn_on(rest):
    """input_boolean turn_on sets state to on."""
    await rest.set_state("input_boolean.depth_ib1", "off")
    await rest.call_service("input_boolean", "turn_on", {
        "entity_id": "input_boolean.depth_ib1",
    })
    state = await rest.get_state("input_boolean.depth_ib1")
    assert state["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean turn_off sets state to off."""
    await rest.set_state("input_boolean.depth_ib2", "on")
    await rest.call_service("input_boolean", "turn_off", {
        "entity_id": "input_boolean.depth_ib2",
    })
    state = await rest.get_state("input_boolean.depth_ib2")
    assert state["state"] == "off"


async def test_input_boolean_toggle(rest):
    """input_boolean toggle flips state."""
    await rest.set_state("input_boolean.depth_ib3", "on")
    await rest.call_service("input_boolean", "toggle", {
        "entity_id": "input_boolean.depth_ib3",
    })
    state = await rest.get_state("input_boolean.depth_ib3")
    assert state["state"] == "off"


async def test_input_boolean_toggle_from_off(rest):
    """input_boolean toggle from off goes to on."""
    await rest.set_state("input_boolean.depth_ib4", "off")
    await rest.call_service("input_boolean", "toggle", {
        "entity_id": "input_boolean.depth_ib4",
    })
    state = await rest.get_state("input_boolean.depth_ib4")
    assert state["state"] == "on"


# ── Input Number ─────────────────────────────────────────

async def test_input_number_set_value(rest):
    """input_number set_value stores value as state."""
    await rest.set_state("input_number.depth_in1", "0")
    await rest.call_service("input_number", "set_value", {
        "entity_id": "input_number.depth_in1",
        "value": 42,
    })
    state = await rest.get_state("input_number.depth_in1")
    assert "42" in state["state"]


async def test_input_number_set_float(rest):
    """input_number set_value with float."""
    await rest.set_state("input_number.depth_in2", "0")
    await rest.call_service("input_number", "set_value", {
        "entity_id": "input_number.depth_in2",
        "value": 3.14,
    })
    state = await rest.get_state("input_number.depth_in2")
    assert "3.14" in state["state"]


# ── Input Text ───────────────────────────────────────────

async def test_input_text_set_value(rest):
    """input_text set_value stores text as state."""
    await rest.set_state("input_text.depth_it1", "")
    await rest.call_service("input_text", "set_value", {
        "entity_id": "input_text.depth_it1",
        "value": "hello world",
    })
    state = await rest.get_state("input_text.depth_it1")
    assert state["state"] == "hello world"


async def test_input_text_set_empty(rest):
    """input_text set_value with empty string."""
    await rest.set_state("input_text.depth_it2", "something")
    await rest.call_service("input_text", "set_value", {
        "entity_id": "input_text.depth_it2",
        "value": "",
    })
    state = await rest.get_state("input_text.depth_it2")
    assert state["state"] == ""


# ── Input Select ─────────────────────────────────────────

async def test_input_select_option(rest):
    """input_select select_option changes state."""
    await rest.set_state("input_select.depth_is1", "option_a")
    await rest.call_service("input_select", "select_option", {
        "entity_id": "input_select.depth_is1",
        "option": "option_b",
    })
    state = await rest.get_state("input_select.depth_is1")
    assert state["state"] == "option_b"


# ── Input Datetime ───────────────────────────────────────

async def test_input_datetime_set_date(rest):
    """input_datetime set_datetime with date value."""
    await rest.set_state("input_datetime.depth_id1", "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": "input_datetime.depth_id1",
        "date": "2026-02-14",
    })
    state = await rest.get_state("input_datetime.depth_id1")
    assert "2026-02-14" in state["state"]


async def test_input_datetime_set_time(rest):
    """input_datetime set_datetime with time value."""
    await rest.set_state("input_datetime.depth_id2", "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": "input_datetime.depth_id2",
        "time": "14:30:00",
    })
    state = await rest.get_state("input_datetime.depth_id2")
    assert "14:30:00" in state["state"]
