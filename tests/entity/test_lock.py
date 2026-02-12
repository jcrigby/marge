"""CTS — Lock Entity Tests."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_lock_locks(rest):
    entity_id = "lock.test_lock"
    await rest.set_state(entity_id, "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "locked"


async def test_lock_unlocks(rest):
    entity_id = "lock.test_unlock"
    await rest.set_state(entity_id, "locked")
    await rest.call_service("lock", "unlock", {"entity_id": entity_id})
    state = await rest.get_state(entity_id)
    assert state["state"] == "unlocked"
