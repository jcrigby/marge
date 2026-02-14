"""
CTS -- Concurrent Operation Tests

Tests concurrent REST API operations: parallel state sets,
parallel service calls, mixed read/write, and data consistency.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_concurrent_state_sets(rest):
    """Concurrent state sets to different entities all succeed."""
    tag = uuid.uuid4().hex[:8]
    n = 20

    async def set_one(i):
        eid = f"sensor.conc_set_{tag}_{i}"
        await rest.set_state(eid, f"val_{i}")
        return eid

    eids = await asyncio.gather(*[set_one(i) for i in range(n)])

    for i, eid in enumerate(eids):
        state = await rest.get_state(eid)
        assert state["state"] == f"val_{i}"


async def test_concurrent_reads(rest):
    """Concurrent reads don't interfere with each other."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.conc_read_{tag}"
    await rest.set_state(eid, "stable")

    async def read_one():
        state = await rest.get_state(eid)
        return state["state"]

    results = await asyncio.gather(*[read_one() for _ in range(20)])
    assert all(r == "stable" for r in results)


async def test_concurrent_same_entity(rest):
    """Concurrent writes to same entity don't crash."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.conc_same_{tag}"

    async def write_one(i):
        await rest.set_state(eid, str(i))

    await asyncio.gather(*[write_one(i) for i in range(20)])

    # Final state should be one of the written values
    state = await rest.get_state(eid)
    assert int(state["state"]) in range(20)


async def test_concurrent_service_calls(rest):
    """Concurrent service calls all complete."""
    tag = uuid.uuid4().hex[:8]

    async def call_one(i):
        eid = f"light.conc_svc_{tag}_{i}"
        await rest.set_state(eid, "off")
        resp = await rest.client.post(
            f"{rest.base_url}/api/services/light/turn_on",
            json={"entity_id": eid},
            headers=rest._headers(),
        )
        return resp.status_code

    results = await asyncio.gather(*[call_one(i) for i in range(10)])
    assert all(r == 200 for r in results)

    # All should be on
    for i in range(10):
        state = await rest.get_state(f"light.conc_svc_{tag}_{i}")
        assert state["state"] == "on"


async def test_concurrent_mixed_operations(rest):
    """Mixed concurrent reads and writes don't crash."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.conc_mix_{tag}"
    await rest.set_state(eid, "initial")

    async def write_op(i):
        await rest.set_state(eid, f"write_{i}")

    async def read_op():
        state = await rest.get_state(eid)
        assert state is not None

    ops = []
    for i in range(10):
        ops.append(write_op(i))
        ops.append(read_op())

    await asyncio.gather(*ops)


async def test_concurrent_get_states(rest):
    """Concurrent GET /api/states calls all succeed."""
    async def get_all():
        resp = await rest.client.get(
            f"{rest.base_url}/api/states",
            headers=rest._headers(),
        )
        assert resp.status_code == 200
        return len(resp.json())

    results = await asyncio.gather(*[get_all() for _ in range(10)])
    # All should return same count (no writes during reads)
    assert all(r == results[0] for r in results)


async def test_concurrent_search(rest):
    """Concurrent search calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.conc_search_{tag}", "val")

    async def search_one():
        resp = await rest.client.get(
            f"{rest.base_url}/api/states/search",
            params={"q": f"conc_search_{tag}"},
            headers=rest._headers(),
        )
        assert resp.status_code == 200
        return len(resp.json())

    results = await asyncio.gather(*[search_one() for _ in range(10)])
    assert all(r >= 1 for r in results)


async def test_concurrent_template_renders(rest):
    """Concurrent template renders all succeed."""
    async def render_one(i):
        resp = await rest.client.post(
            f"{rest.base_url}/api/template",
            json={"template": f"{{{{ {i} + 1 }}}}"},
            headers=rest._headers(),
        )
        assert resp.status_code == 200
        return resp.text.strip()

    results = await asyncio.gather(*[render_one(i) for i in range(10)])
    for i, r in enumerate(results):
        assert r == str(i + 1)
