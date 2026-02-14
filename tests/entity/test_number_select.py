"""
CTS -- Number and Select Entity Tests

Tests number and select domain services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Number ────────────────────────────────


async def test_number_set_value(rest):
    """number.set_value updates state."""
    entity_id = "number.test_val"
    await rest.set_state(entity_id, "0", {"min": 0, "max": 100, "step": 1})
    await rest.call_service("number", "set_value", {
        "entity_id": entity_id,
        "value": 55,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "55"


async def test_number_set_float_value(rest):
    """number.set_value handles float values."""
    entity_id = "number.test_float"
    await rest.set_state(entity_id, "0", {"min": 0, "max": 10, "step": 0.1})
    await rest.call_service("number", "set_value", {
        "entity_id": entity_id,
        "value": 3.14,
    })

    state = await rest.get_state(entity_id)
    assert "3.14" in state["state"]


# ── Select ────────────────────────────────


async def test_select_option(rest):
    """select.select_option changes state."""
    entity_id = "select.test_sel"
    await rest.set_state(entity_id, "auto", {"options": ["auto", "manual", "eco"]})
    await rest.call_service("select", "select_option", {
        "entity_id": entity_id,
        "option": "eco",
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "eco"


async def test_select_preserves_options(rest):
    """select.select_option preserves the options attribute."""
    entity_id = "select.test_opts"
    options = ["low", "medium", "high"]
    await rest.set_state(entity_id, "low", {"options": options})
    await rest.call_service("select", "select_option", {
        "entity_id": entity_id,
        "option": "high",
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["options"] == options
