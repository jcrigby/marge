"""
CTS -- Cover Service Handler Depth Tests

Tests cover domain service handlers: open, close, stop, toggle,
set_cover_position, and position-based state transitions.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_open_cover(rest):
    """open_cover sets state to open and position to 100."""
    await rest.set_state("cover.depth_open", "closed", {"current_position": 0})
    await rest.call_service("cover", "open_cover", {"entity_id": "cover.depth_open"})
    state = await rest.get_state("cover.depth_open")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_close_cover(rest):
    """close_cover sets state to closed and position to 0."""
    await rest.set_state("cover.depth_close", "open", {"current_position": 100})
    await rest.call_service("cover", "close_cover", {"entity_id": "cover.depth_close"})
    state = await rest.get_state("cover.depth_close")
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_stop_cover_preserves_state(rest):
    """stop_cover preserves the current state."""
    await rest.set_state("cover.depth_stop", "open", {"current_position": 50})
    await rest.call_service("cover", "stop_cover", {"entity_id": "cover.depth_stop"})
    state = await rest.get_state("cover.depth_stop")
    assert state["state"] == "open"


async def test_toggle_cover_open_to_closed(rest):
    """toggle from open sets state to closed."""
    await rest.set_state("cover.depth_tog1", "open", {"current_position": 100})
    await rest.call_service("cover", "toggle", {"entity_id": "cover.depth_tog1"})
    state = await rest.get_state("cover.depth_tog1")
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_toggle_cover_closed_to_open(rest):
    """toggle from closed sets state to open."""
    await rest.set_state("cover.depth_tog2", "closed", {"current_position": 0})
    await rest.call_service("cover", "toggle", {"entity_id": "cover.depth_tog2"})
    state = await rest.get_state("cover.depth_tog2")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_set_cover_position_mid(rest):
    """set_cover_position to 50 sets state to open."""
    await rest.set_state("cover.depth_pos1", "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.depth_pos1",
        "position": 50,
    })
    state = await rest.get_state("cover.depth_pos1")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


async def test_set_cover_position_zero(rest):
    """set_cover_position to 0 sets state to closed."""
    await rest.set_state("cover.depth_pos0", "open")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.depth_pos0",
        "position": 0,
    })
    state = await rest.get_state("cover.depth_pos0")
    assert state["state"] == "closed"


async def test_set_cover_position_full(rest):
    """set_cover_position to 100 sets state to open."""
    await rest.set_state("cover.depth_full", "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.depth_full",
        "position": 100,
    })
    state = await rest.get_state("cover.depth_full")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100
