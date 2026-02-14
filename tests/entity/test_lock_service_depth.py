"""
CTS -- Lock Service Handler Depth Tests

Tests lock domain services: lock, unlock, open, state transitions,
and attribute preservation.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_lock_sets_locked(rest):
    """lock service sets state to locked."""
    await rest.set_state("lock.depth_l1", "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": "lock.depth_l1"})
    state = await rest.get_state("lock.depth_l1")
    assert state["state"] == "locked"


async def test_unlock_sets_unlocked(rest):
    """unlock service sets state to unlocked."""
    await rest.set_state("lock.depth_l2", "locked")
    await rest.call_service("lock", "unlock", {"entity_id": "lock.depth_l2"})
    state = await rest.get_state("lock.depth_l2")
    assert state["state"] == "unlocked"


async def test_lock_open(rest):
    """open service sets state to open."""
    await rest.set_state("lock.depth_l3", "locked")
    await rest.call_service("lock", "open", {"entity_id": "lock.depth_l3"})
    state = await rest.get_state("lock.depth_l3")
    assert state["state"] == "open"


async def test_lock_cycle(rest):
    """Full lock cycle: unlocked -> locked -> unlocked."""
    eid = "lock.depth_cycle"
    await rest.set_state(eid, "unlocked")

    await rest.call_service("lock", "lock", {"entity_id": eid})
    s1 = await rest.get_state(eid)
    assert s1["state"] == "locked"

    await rest.call_service("lock", "unlock", {"entity_id": eid})
    s2 = await rest.get_state(eid)
    assert s2["state"] == "unlocked"


async def test_lock_preserves_attrs(rest):
    """Lock service preserves existing attributes."""
    await rest.set_state("lock.depth_attr", "unlocked", {"battery": 85})
    await rest.call_service("lock", "lock", {"entity_id": "lock.depth_attr"})
    state = await rest.get_state("lock.depth_attr")
    assert state["state"] == "locked"
    assert state["attributes"]["battery"] == 85


async def test_lock_open_from_unlocked(rest):
    """Open from unlocked state."""
    await rest.set_state("lock.depth_open2", "unlocked")
    await rest.call_service("lock", "open", {"entity_id": "lock.depth_open2"})
    state = await rest.get_state("lock.depth_open2")
    assert state["state"] == "open"
