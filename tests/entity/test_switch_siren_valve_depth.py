"""
CTS -- Switch, Siren, and Valve Service Depth Tests

Tests switch (turn_on, turn_off, toggle), siren (turn_on, turn_off,
toggle), and valve (open_valve, close_valve, toggle) domain handlers.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Switch ───────────────────────────────────────────────

async def test_switch_turn_on(rest):
    """switch turn_on sets state to on."""
    await rest.set_state("switch.depth_sw1", "off")
    await rest.call_service("switch", "turn_on", {"entity_id": "switch.depth_sw1"})
    state = await rest.get_state("switch.depth_sw1")
    assert state["state"] == "on"


async def test_switch_turn_off(rest):
    """switch turn_off sets state to off."""
    await rest.set_state("switch.depth_sw2", "on")
    await rest.call_service("switch", "turn_off", {"entity_id": "switch.depth_sw2"})
    state = await rest.get_state("switch.depth_sw2")
    assert state["state"] == "off"


async def test_switch_toggle_on_to_off(rest):
    """switch toggle from on to off."""
    await rest.set_state("switch.depth_sw3", "on")
    await rest.call_service("switch", "toggle", {"entity_id": "switch.depth_sw3"})
    state = await rest.get_state("switch.depth_sw3")
    assert state["state"] == "off"


async def test_switch_toggle_off_to_on(rest):
    """switch toggle from off to on."""
    await rest.set_state("switch.depth_sw4", "off")
    await rest.call_service("switch", "toggle", {"entity_id": "switch.depth_sw4"})
    state = await rest.get_state("switch.depth_sw4")
    assert state["state"] == "on"


async def test_switch_preserves_attrs(rest):
    """switch turn_on preserves attributes."""
    await rest.set_state("switch.depth_sw5", "off", {"device_class": "outlet"})
    await rest.call_service("switch", "turn_on", {"entity_id": "switch.depth_sw5"})
    state = await rest.get_state("switch.depth_sw5")
    assert state["state"] == "on"
    assert state["attributes"]["device_class"] == "outlet"


# ── Siren ────────────────────────────────────────────────

async def test_siren_turn_on(rest):
    """siren turn_on sets state to on."""
    await rest.set_state("siren.depth_si1", "off")
    await rest.call_service("siren", "turn_on", {"entity_id": "siren.depth_si1"})
    state = await rest.get_state("siren.depth_si1")
    assert state["state"] == "on"


async def test_siren_turn_off(rest):
    """siren turn_off sets state to off."""
    await rest.set_state("siren.depth_si2", "on")
    await rest.call_service("siren", "turn_off", {"entity_id": "siren.depth_si2"})
    state = await rest.get_state("siren.depth_si2")
    assert state["state"] == "off"


async def test_siren_toggle(rest):
    """siren toggle from on to off."""
    await rest.set_state("siren.depth_si3", "on")
    await rest.call_service("siren", "toggle", {"entity_id": "siren.depth_si3"})
    state = await rest.get_state("siren.depth_si3")
    assert state["state"] == "off"


async def test_siren_toggle_off_to_on(rest):
    """siren toggle from off to on."""
    await rest.set_state("siren.depth_si4", "off")
    await rest.call_service("siren", "toggle", {"entity_id": "siren.depth_si4"})
    state = await rest.get_state("siren.depth_si4")
    assert state["state"] == "on"


# ── Valve ────────────────────────────────────────────────

async def test_valve_open(rest):
    """valve open_valve sets state to open."""
    await rest.set_state("valve.depth_v1", "closed")
    await rest.call_service("valve", "open_valve", {"entity_id": "valve.depth_v1"})
    state = await rest.get_state("valve.depth_v1")
    assert state["state"] == "open"


async def test_valve_close(rest):
    """valve close_valve sets state to closed."""
    await rest.set_state("valve.depth_v2", "open")
    await rest.call_service("valve", "close_valve", {"entity_id": "valve.depth_v2"})
    state = await rest.get_state("valve.depth_v2")
    assert state["state"] == "closed"


async def test_valve_toggle_open_to_closed(rest):
    """valve toggle from open to closed."""
    await rest.set_state("valve.depth_v3", "open")
    await rest.call_service("valve", "toggle", {"entity_id": "valve.depth_v3"})
    state = await rest.get_state("valve.depth_v3")
    assert state["state"] == "closed"


async def test_valve_toggle_closed_to_open(rest):
    """valve toggle from closed to open."""
    await rest.set_state("valve.depth_v4", "closed")
    await rest.call_service("valve", "toggle", {"entity_id": "valve.depth_v4"})
    state = await rest.get_state("valve.depth_v4")
    assert state["state"] == "open"
