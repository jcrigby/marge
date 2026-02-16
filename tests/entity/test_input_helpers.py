"""
CTS -- Input Helper Entity Tests

Tests input_number attribute preservation and input_select option preservation.
"""

import pytest

pytestmark = pytest.mark.asyncio


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
