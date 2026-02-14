"""
CTS -- Siren and Valve Entity Tests

Tests siren and valve domain services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Siren ────────────────────────────────────────


async def test_siren_turn_on(rest):
    """siren.turn_on sets state to 'on'."""
    entity_id = "siren.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("siren", "turn_on", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_siren_turn_off(rest):
    """siren.turn_off sets state to 'off'."""
    entity_id = "siren.test_off"
    await rest.set_state(entity_id, "on")
    await rest.call_service("siren", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_siren_toggle(rest):
    """siren.toggle flips state."""
    entity_id = "siren.test_toggle"
    await rest.set_state(entity_id, "off")
    await rest.call_service("siren", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"

    await rest.call_service("siren", "toggle", {"entity_id": entity_id})
    state2 = await rest.get_state(entity_id)
    assert state2["state"] == "off"


# ── Valve ────────────────────────────────────────


async def test_valve_open(rest):
    """valve.open_valve sets state to 'open'."""
    entity_id = "valve.test_open"
    await rest.set_state(entity_id, "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "open"


async def test_valve_close(rest):
    """valve.close_valve sets state to 'closed'."""
    entity_id = "valve.test_close"
    await rest.set_state(entity_id, "open")
    await rest.call_service("valve", "close_valve", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "closed"


async def test_valve_toggle(rest):
    """valve.toggle flips state."""
    entity_id = "valve.test_toggle"
    await rest.set_state(entity_id, "open")
    await rest.call_service("valve", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "closed"

    await rest.call_service("valve", "toggle", {"entity_id": entity_id})
    state2 = await rest.get_state(entity_id)
    assert state2["state"] == "open"
