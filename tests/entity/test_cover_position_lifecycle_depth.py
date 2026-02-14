"""
CTS -- Cover Position Lifecycle Depth Tests

Tests cover domain service handlers with position tracking:
open (pos=100), close (pos=0), stop (preserve state), toggle
(flip state + position), set_cover_position, and position-based
state inference.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Open/Close Position ──────────────────────────────────

async def test_cover_open_sets_position_100(rest):
    """cover.open_cover sets current_position to 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_open_{tag}"
    await rest.set_state(eid, "closed", {"current_position": 0})
    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_close_sets_position_0(rest):
    """cover.close_cover sets current_position to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_close_{tag}"
    await rest.set_state(eid, "open", {"current_position": 100})
    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_stop_preserves_state(rest):
    """cover.stop_cover preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_stop_{tag}"
    await rest.set_state(eid, "open", {"current_position": 50})
    await rest.call_service("cover", "stop_cover", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"


# ── Toggle ───────────────────────────────────────────────

async def test_cover_toggle_open_to_closed(rest):
    """cover.toggle from open → closed, position 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_tog1_{tag}"
    await rest.set_state(eid, "open", {"current_position": 100})
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_toggle_closed_to_open(rest):
    """cover.toggle from closed → open, position 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_tog2_{tag}"
    await rest.set_state(eid, "closed", {"current_position": 0})
    await rest.call_service("cover", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


# ── Set Position ─────────────────────────────────────────

async def test_cover_set_position_midrange(rest):
    """cover.set_cover_position at 50 sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_pos50_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 50,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


async def test_cover_set_position_zero_closed(rest):
    """cover.set_cover_position at 0 sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_pos0_{tag}"
    await rest.set_state(eid, "open")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 0,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_cover_set_position_100_open(rest):
    """cover.set_cover_position at 100 sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_pos100_{tag}"
    await rest.set_state(eid, "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 100,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


# ── Full Lifecycle ───────────────────────────────────────

async def test_cover_full_lifecycle(rest):
    """Cover: closed → open → set_pos(30) → close → toggle → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cpld_lc_{tag}"
    await rest.set_state(eid, "closed", {"current_position": 0})

    await rest.call_service("cover", "open_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"

    await rest.call_service("cover", "set_cover_position", {
        "entity_id": eid, "position": 30,
    })
    assert (await rest.get_state(eid))["attributes"]["current_position"] == 30

    await rest.call_service("cover", "close_cover", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "closed"

    await rest.call_service("cover", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "open"
