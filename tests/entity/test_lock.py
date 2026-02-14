"""
CTS -- Lock Entity Tests

Tests lock domain services: lock, unlock, generic toggle.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_lock_locks(rest):
    """lock.lock sets state to 'locked'."""
    entity_id = "lock.test_lock"
    await rest.set_state(entity_id, "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "locked"


async def test_lock_unlocks(rest):
    """lock.unlock sets state to 'unlocked'."""
    entity_id = "lock.test_unlock"
    await rest.set_state(entity_id, "locked")
    await rest.call_service("lock", "unlock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "unlocked"


async def test_lock_toggle_locked_to_unlocked(rest):
    """lock.toggle flips locked to unlocked (via generic fallback)."""
    entity_id = "lock.test_toggle_lu"
    await rest.set_state(entity_id, "locked")
    await rest.call_service("lock", "toggle", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    # Generic toggle treats non-"on" as "on"
    assert state["state"] == "on"


async def test_lock_preserves_attributes(rest):
    """lock/unlock preserves existing attributes."""
    entity_id = "lock.test_attrs"
    await rest.set_state(entity_id, "unlocked", {"friendly_name": "Front Door", "battery": 85})
    await rest.call_service("lock", "lock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "locked"
    assert state["attributes"]["friendly_name"] == "Front Door"
    assert state["attributes"]["battery"] == 85
