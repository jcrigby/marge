"""
CTS -- Homeassistant Domain, Group, Update, Input Datetime Entity Tests

Tests homeassistant.turn_on/turn_off/toggle, group.set,
update.install/skip, input_datetime.set_datetime.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Homeassistant domain ──────────────────────────────────

async def test_homeassistant_turn_on(rest):
    """homeassistant.turn_on sets entity to 'on'."""
    entity_id = "switch.ha_svc_test"
    await rest.set_state(entity_id, "off")
    await rest.call_service("homeassistant", "turn_on", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_homeassistant_turn_off(rest):
    """homeassistant.turn_off sets entity to 'off'."""
    entity_id = "light.ha_svc_test"
    await rest.set_state(entity_id, "on")
    await rest.call_service("homeassistant", "turn_off", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_homeassistant_toggle(rest):
    """homeassistant.toggle flips entity state."""
    entity_id = "switch.ha_toggle_test"
    await rest.set_state(entity_id, "on")
    await rest.call_service("homeassistant", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


# ── Group domain ──────────────────────────────────────────

async def test_group_set(rest):
    """group.set sets group state."""
    entity_id = "group.test_group"
    await rest.set_state(entity_id, "off")
    await rest.call_service("group", "set", {
        "entity_id": entity_id,
        "state": "on",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


# ── Update domain ─────────────────────────────────────────

async def test_update_install(rest):
    """update.install sets state to 'installing'."""
    entity_id = "update.test_update"
    await rest.set_state(entity_id, "available")
    await rest.call_service("update", "install", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "installing"


async def test_update_skip(rest):
    """update.skip sets state to 'skipped'."""
    entity_id = "update.test_skip"
    await rest.set_state(entity_id, "available")
    await rest.call_service("update", "skip", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "skipped"


# ── Input Datetime ────────────────────────────────────────

async def test_input_datetime_set(rest):
    """input_datetime.set_datetime updates the datetime state."""
    entity_id = "input_datetime.test_dt"
    await rest.set_state(entity_id, "2024-01-01 00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": entity_id,
        "datetime": "2024-06-15 14:30",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "2024-06-15 14:30"


async def test_input_datetime_set_time(rest):
    """input_datetime.set_datetime with time-only updates state."""
    entity_id = "input_datetime.test_time"
    await rest.set_state(entity_id, "00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": entity_id,
        "time": "19:45",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "19:45"
