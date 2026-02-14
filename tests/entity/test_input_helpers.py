"""
CTS -- Input Helper Entity Tests

Tests input_boolean, input_number, input_select, input_text domain services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── input_boolean ────────────────────────────────


async def test_input_boolean_turn_on(rest):
    """input_boolean.turn_on sets state to 'on'."""
    entity_id = "input_boolean.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("input_boolean", "turn_on", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean.turn_off sets state to 'off'."""
    entity_id = "input_boolean.test_off"
    await rest.set_state(entity_id, "on")
    await rest.call_service("input_boolean", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_input_boolean_toggle(rest):
    """input_boolean.toggle flips state."""
    entity_id = "input_boolean.test_toggle"
    await rest.set_state(entity_id, "off")
    await rest.call_service("input_boolean", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"

    await rest.call_service("input_boolean", "toggle", {"entity_id": entity_id})
    state2 = await rest.get_state(entity_id)
    assert state2["state"] == "off"


# ── input_number ────────────────────────────────


async def test_input_number_set_value(rest):
    """input_number.set_value updates state."""
    entity_id = "input_number.test_val"
    await rest.set_state(entity_id, "0", {"min": 0, "max": 100, "step": 1})
    await rest.call_service("input_number", "set_value", {
        "entity_id": entity_id,
        "value": 42,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "42"


async def test_input_number_preserves_attributes(rest):
    """input_number.set_value preserves min/max/step attributes."""
    entity_id = "input_number.test_attrs"
    await rest.set_state(entity_id, "10", {"min": 0, "max": 200, "step": 5})
    await rest.call_service("input_number", "set_value", {
        "entity_id": entity_id,
        "value": 75,
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["min"] == 0
    assert state["attributes"]["max"] == 200
    assert state["attributes"]["step"] == 5


# ── input_select ────────────────────────────────


async def test_input_select_select_option(rest):
    """input_select.select_option changes state to selected option."""
    entity_id = "input_select.test_sel"
    await rest.set_state(entity_id, "option_a", {"options": ["option_a", "option_b", "option_c"]})
    await rest.call_service("input_select", "select_option", {
        "entity_id": entity_id,
        "option": "option_b",
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "option_b"


async def test_input_select_preserves_options(rest):
    """input_select.select_option preserves the options list."""
    entity_id = "input_select.test_opts"
    options = ["low", "medium", "high"]
    await rest.set_state(entity_id, "low", {"options": options})
    await rest.call_service("input_select", "select_option", {
        "entity_id": entity_id,
        "option": "high",
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["options"] == options


# ── input_text ────────────────────────────────


async def test_input_text_set_value(rest):
    """input_text.set_value changes the text state."""
    entity_id = "input_text.test_txt"
    await rest.set_state(entity_id, "old text")
    await rest.call_service("input_text", "set_value", {
        "entity_id": entity_id,
        "value": "new text",
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "new text"


async def test_input_text_set_empty(rest):
    """input_text.set_value can set empty string."""
    entity_id = "input_text.test_empty"
    await rest.set_state(entity_id, "some text")
    await rest.call_service("input_text", "set_value", {
        "entity_id": entity_id,
        "value": "",
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == ""
