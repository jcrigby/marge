"""
CTS -- Cover Entity Tests

Tests cover domain services: open_cover, close_cover, stop_cover, set_cover_position (zero).
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_cover_open(rest):
    """cover.open_cover sets state to 'open' and position to 100."""
    entity_id = "cover.test_open"
    await rest.set_state(entity_id, "closed", {"current_position": 0})
    await rest.call_service("cover", "open_cover", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_close(rest):
    """cover.close_cover sets state to 'closed' and position to 0."""
    entity_id = "cover.test_close"
    await rest.set_state(entity_id, "open", {"current_position": 100})
    await rest.call_service("cover", "close_cover", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_stop(rest):
    """cover.stop_cover preserves current state and position."""
    entity_id = "cover.test_stop"
    await rest.set_state(entity_id, "opening", {"current_position": 65})
    await rest.call_service("cover", "stop_cover", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "opening"
    assert state["attributes"]["current_position"] == 65


async def test_cover_set_position_zero(rest):
    """cover.set_cover_position to 0 results in 'closed' state."""
    entity_id = "cover.test_setpos_zero"
    await rest.set_state(entity_id, "open", {"current_position": 50})
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": entity_id,
        "position": 0,
    })

    state = await rest.get_state(entity_id)
    assert state["state"] == "closed"
