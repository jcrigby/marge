"""
CTS -- Vacuum Entity Tests

Tests vacuum domain services: start, stop, pause, return_to_base.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_vacuum_start(rest):
    """vacuum.start sets state to 'cleaning'."""
    entity_id = "vacuum.test_start"
    await rest.set_state(entity_id, "docked")
    await rest.call_service("vacuum", "start", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "cleaning"


async def test_vacuum_stop(rest):
    """vacuum.stop sets state to 'idle'."""
    entity_id = "vacuum.test_stop"
    await rest.set_state(entity_id, "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "idle"


async def test_vacuum_pause(rest):
    """vacuum.pause sets state to 'paused'."""
    entity_id = "vacuum.test_pause"
    await rest.set_state(entity_id, "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to 'returning'."""
    entity_id = "vacuum.test_dock"
    await rest.set_state(entity_id, "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "returning"


async def test_vacuum_lifecycle(rest):
    """Full vacuum lifecycle: docked -> cleaning -> paused -> cleaning -> returning."""
    entity_id = "vacuum.test_lifecycle"
    await rest.set_state(entity_id, "docked")

    await rest.call_service("vacuum", "start", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "paused"

    await rest.call_service("vacuum", "start", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "cleaning"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "returning"
