"""
CTS -- Cover and Fan Service Depth Tests

Tests cover services (open, close, stop, toggle, set_position)
and fan services (turn_on with percentage, set_direction,
set_preset_mode, set_percentage).
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Cover Open/Close ───────────────────────────────────────

async def test_cover_open(rest):
    """cover.open_cover sets state to open and position to 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_{tag}"
    await rest.set_state(eid, "closed", {"current_position": 0})
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_close(rest):
    """cover.close_cover sets state to closed and position to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_cls_{tag}"
    await rest.set_state(eid, "open", {"current_position": 100})
    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_stop(rest):
    """cover.stop_cover preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_stop_{tag}"
    await rest.set_state(eid, "open", {"current_position": 50})
    await rest.call_service("cover", "stop_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_cover_toggle_closed_to_open(rest):
    """cover.toggle: closed → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_tog_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"


async def test_cover_toggle_open_to_closed(rest):
    """cover.toggle: open → closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_tog2_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"


async def test_cover_set_position(rest):
    """cover.set_cover_position sets position attribute and state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_pos_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 75
    })
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 75


async def test_cover_set_position_zero_is_closed(rest):
    """cover.set_cover_position at 0 sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cvr_pos0_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 0
    })
    assert (await rest.get_state(eid))["state"] == "closed"


# ── Fan Turn On/Off ────────────────────────────────────────

async def test_fan_turn_on(rest):
    """fan.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_fan_turn_on_with_percentage(rest):
    """fan.turn_on with percentage sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_pct_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "turn_on", {
        "entity_id": eid, "percentage": 75
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_turn_off(rest):
    """fan.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_fan_toggle(rest):
    """fan.toggle flips on ↔ off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_tog_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"
    await rest.call_service("fan", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


# ── Fan set_direction ──────────────────────────────────────

async def test_fan_set_direction(rest):
    """fan.set_direction sets direction attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_dir_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_direction", {
        "entity_id": eid, "direction": "reverse"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["direction"] == "reverse"


# ── Fan set_preset_mode ────────────────────────────────────

async def test_fan_set_preset_mode(rest):
    """fan.set_preset_mode sets preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_preset_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": eid, "preset_mode": "sleep"
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "sleep"


# ── Fan set_percentage ─────────────────────────────────────

async def test_fan_set_percentage(rest):
    """fan.set_percentage sets percentage and keeps on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_spct_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 50
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 50


async def test_fan_set_percentage_zero_turns_off(rest):
    """fan.set_percentage at 0 turns off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fn_spct0_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": eid, "percentage": 0
    })
    assert (await rest.get_state(eid))["state"] == "off"
