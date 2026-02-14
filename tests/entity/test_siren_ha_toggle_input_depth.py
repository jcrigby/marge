"""
CTS -- Siren, Homeassistant Toggle, and Input Boolean Depth Tests

Tests siren services (turn_on/off/toggle), homeassistant.turn_on/off/toggle
across arbitrary domains, and input_boolean lifecycle.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Siren ─────────────────────────────────────────────────

async def test_siren_turn_on(rest):
    """siren.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sir_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_siren_turn_off(rest):
    """siren.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sir_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_siren_toggle_on_to_off(rest):
    """siren.toggle: on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sir_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_siren_toggle_off_to_on(rest):
    """siren.toggle: off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sir_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_siren_lifecycle(rest):
    """Siren: off → on → toggle → off → toggle → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"siren.sir_life_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("siren", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"

    await rest.call_service("siren", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Homeassistant turn_on / turn_off / toggle ─────────────

async def test_ha_turn_on_light(rest):
    """homeassistant.turn_on sets any entity to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ha_on_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_ha_turn_off_switch(rest):
    """homeassistant.turn_off sets any entity to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ha_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_ha_toggle_on_to_off(rest):
    """homeassistant.toggle: on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.ha_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_ha_toggle_off_to_on(rest):
    """homeassistant.toggle: off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ha_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_ha_turn_on_preserves_attrs(rest):
    """homeassistant.turn_on preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ha_attr_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": "Test", "unit": "W"})
    await rest.call_service("homeassistant", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["friendly_name"] == "Test"
    assert state["attributes"]["unit"] == "W"


async def test_ha_toggle_unknown_becomes_on(rest):
    """homeassistant.toggle on unknown state → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ha_unk_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("homeassistant", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Input Boolean ─────────────────────────────────────────

async def test_input_boolean_turn_on(rest):
    """input_boolean.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("input_boolean", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_input_boolean_turn_off(rest):
    """input_boolean.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("input_boolean", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_input_boolean_toggle(rest):
    """input_boolean.toggle flips on ↔ off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_input_boolean_lifecycle(rest):
    """Input boolean: off → on → toggle → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_boolean.ib_life_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("input_boolean", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("input_boolean", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"

    await rest.call_service("input_boolean", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("input_boolean", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
