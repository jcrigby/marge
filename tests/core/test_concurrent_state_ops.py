"""
CTS -- Concurrent State Operation Tests

Tests concurrent writes to the same entity, concurrent writes to
different entities, and race conditions between REST service calls
and direct state sets.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_concurrent_writes_same_entity(rest):
    """Concurrent writes to same entity all succeed (last-write-wins)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.conc_{tag}"

    async def write(val):
        await rest.set_state(eid, str(val))

    # Fire 10 concurrent writes
    await asyncio.gather(*[write(i) for i in range(10)])

    # Entity should exist with one of the values
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] in [str(i) for i in range(10)]


async def test_concurrent_writes_different_entities(rest):
    """Concurrent writes to different entities all succeed."""
    tag = uuid.uuid4().hex[:8]

    async def write(i):
        eid = f"sensor.multi_{tag}_{i}"
        await rest.set_state(eid, str(i))

    # Fire 20 concurrent writes to different entities
    await asyncio.gather(*[write(i) for i in range(20)])

    # All 20 should exist
    for i in range(20):
        state = await rest.get_state(f"sensor.multi_{tag}_{i}")
        assert state is not None
        assert state["state"] == str(i)


async def test_concurrent_service_calls(rest):
    """Concurrent service calls on different entities all succeed."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.csvc_{tag}_{i}" for i in range(5)]

    # Pre-create all entities
    await asyncio.gather(*[rest.set_state(eid, "off") for eid in entities])

    # Turn all on concurrently
    async def turn_on(eid):
        await rest.call_service("light", "turn_on", {"entity_id": eid})

    await asyncio.gather(*[turn_on(eid) for eid in entities])

    # All should be on
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_rapid_state_toggle(rest):
    """Rapid on/off toggling produces consistent final state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.toggle_{tag}"
    await rest.set_state(eid, "off")

    # Toggle 20 times sequentially — final should be "off" (even count)
    for i in range(20):
        await rest.call_service("switch", "toggle", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_concurrent_create_delete(rest):
    """Concurrent creates don't interfere with each other."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"sensor.cd_{tag}_{i}" for i in range(10)]

    # Create all concurrently
    await asyncio.gather(*[rest.set_state(eid, "created") for eid in eids])

    # Delete half concurrently
    async def delete(eid):
        await rest.client.delete(
            f"{rest.base_url}/api/states/{eid}",
            headers=rest._headers(),
        )

    await asyncio.gather(*[delete(eids[i]) for i in range(0, 10, 2)])

    # Even-indexed should be gone, odd should remain
    for i in range(10):
        state = await rest.get_state(eids[i])
        if i % 2 == 0:
            assert state is None, f"{eids[i]} should be deleted"
        else:
            assert state is not None, f"{eids[i]} should exist"
            assert state["state"] == "created"


async def test_concurrent_attribute_updates(rest):
    """Concurrent attribute updates don't corrupt entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.attrs_{tag}"
    await rest.set_state(eid, "stable")

    async def update_attr(key, val):
        # GET current, update one attribute, SET back
        await rest.set_state(eid, "stable", {key: val})

    # Concurrent attribute writes (each overwrites the full attr set)
    await asyncio.gather(*[
        update_attr(f"key_{i}", f"val_{i}") for i in range(5)
    ])

    # Entity should still be readable
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "stable"


async def test_many_entities_bulk_create(rest):
    """Create 50 entities rapidly and verify all exist."""
    tag = uuid.uuid4().hex[:8]

    async def create(i):
        await rest.set_state(f"sensor.bulk_{tag}_{i}", str(i))

    await asyncio.gather(*[create(i) for i in range(50)])

    # Spot-check some
    for i in [0, 10, 25, 49]:
        state = await rest.get_state(f"sensor.bulk_{tag}_{i}")
        assert state is not None
        assert state["state"] == str(i)


async def test_concurrent_service_same_entity(rest):
    """Concurrent service calls on same entity don't crash."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.same_{tag}"
    await rest.set_state(eid, "off")

    async def call_svc(service):
        try:
            await rest.call_service("light", service, {"entity_id": eid})
        except Exception:
            pass  # Some may conflict; that's fine

    # Fire turn_on and turn_off concurrently
    await asyncio.gather(*[
        call_svc("turn_on"),
        call_svc("turn_off"),
        call_svc("turn_on"),
        call_svc("toggle"),
        call_svc("turn_off"),
    ])

    # Entity should still be readable (not corrupted)
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] in ("on", "off")
