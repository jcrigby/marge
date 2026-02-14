"""
CTS -- Concurrent State Operations Depth Tests

Tests concurrent access patterns: parallel state writes, concurrent
service calls, concurrent entity creation/deletion, concurrent history
queries, and verifies data consistency under load.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Parallel State Writes ─────────────────────────────────

async def test_parallel_state_writes(rest):
    """Concurrent writes to different entities succeed independently."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"sensor.par_{i}_{tag}" for i in range(10)]
    await asyncio.gather(*[
        rest.set_state(eid, str(i * 10))
        for i, eid in enumerate(entities)
    ])
    for i, eid in enumerate(entities):
        state = await rest.get_state(eid)
        assert state["state"] == str(i * 10)


async def test_parallel_writes_to_same_entity(rest):
    """Concurrent writes to same entity resolve without crash."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.par_same_{tag}"
    await asyncio.gather(*[
        rest.set_state(eid, str(i))
        for i in range(5)
    ])
    state = await rest.get_state(eid)
    assert state["state"] in [str(i) for i in range(5)]


# ── Concurrent Service Calls ─────────────────────────────

async def test_concurrent_service_calls(rest):
    """Concurrent service calls on different entities."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.csc_{i}_{tag}" for i in range(5)]
    for eid in entities:
        await rest.set_state(eid, "off")
    await asyncio.gather(*[
        rest.call_service("light", "turn_on", {"entity_id": eid})
        for eid in entities
    ])
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_concurrent_mixed_services(rest):
    """Concurrent turn_on and turn_off on different entities."""
    tag = uuid.uuid4().hex[:8]
    on_entities = [f"light.cmix_on_{i}_{tag}" for i in range(3)]
    off_entities = [f"light.cmix_off_{i}_{tag}" for i in range(3)]
    for eid in on_entities:
        await rest.set_state(eid, "off")
    for eid in off_entities:
        await rest.set_state(eid, "on")
    tasks = [
        *[rest.call_service("light", "turn_on", {"entity_id": eid}) for eid in on_entities],
        *[rest.call_service("light", "turn_off", {"entity_id": eid}) for eid in off_entities],
    ]
    await asyncio.gather(*tasks)
    for eid in on_entities:
        assert (await rest.get_state(eid))["state"] == "on"
    for eid in off_entities:
        assert (await rest.get_state(eid))["state"] == "off"


# ── Concurrent Create + Read ──────────────────────────────

async def test_concurrent_create_and_read(rest):
    """Reading entities while creating others doesn't fail."""
    tag = uuid.uuid4().hex[:8]
    # Pre-create some entities
    for i in range(3):
        await rest.set_state(f"sensor.pre_{i}_{tag}", str(i))

    async def create_batch():
        for i in range(3, 6):
            await rest.set_state(f"sensor.pre_{i}_{tag}", str(i))

    async def read_batch():
        for i in range(3):
            state = await rest.get_state(f"sensor.pre_{i}_{tag}")
            assert state is not None

    await asyncio.gather(create_batch(), read_batch())


# ── Concurrent Delete + Read ──────────────────────────────

async def test_concurrent_delete_safety(rest):
    """Deleting entity while reading others is safe."""
    tag = uuid.uuid4().hex[:8]
    eid_keep = f"sensor.keep_{tag}"
    eid_del = f"sensor.del_{tag}"
    await rest.set_state(eid_keep, "42")
    await rest.set_state(eid_del, "99")

    async def delete_entity():
        await rest.client.delete(
            f"{rest.base_url}/api/states/{eid_del}",
            headers=rest._headers(),
        )

    async def read_entity():
        state = await rest.get_state(eid_keep)
        assert state is not None
        assert state["state"] == "42"

    await asyncio.gather(delete_entity(), read_entity())


# ── Concurrent History Reads ──────────────────────────────

async def test_concurrent_history_queries(rest):
    """Concurrent history reads don't block each other."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_conc_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(0.2)
    await rest.set_state(eid, "2")
    await asyncio.sleep(0.3)

    async def query_history():
        resp = await rest.client.get(
            f"{rest.base_url}/api/history/period/{eid}",
            headers=rest._headers(),
        )
        return resp.status_code

    results = await asyncio.gather(*[query_history() for _ in range(5)])
    assert all(r == 200 for r in results)


# ── Burst API Requests ────────────────────────────────────

async def test_burst_api_status(rest):
    """Burst of /api/ requests all succeed."""
    results = await asyncio.gather(*[
        rest.client.get(f"{rest.base_url}/api/", headers=rest._headers())
        for _ in range(20)
    ])
    assert all(r.status_code == 200 for r in results)


async def test_burst_state_reads(rest):
    """Burst reads of same entity are consistent."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.burst_{tag}"
    await rest.set_state(eid, "stable")
    results = await asyncio.gather(*[
        rest.get_state(eid)
        for _ in range(10)
    ])
    assert all(r["state"] == "stable" for r in results)


# ── Concurrent Template Renders ───────────────────────────

async def test_concurrent_template_renders(rest):
    """Concurrent template renders produce correct results."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_conc_{tag}"
    await rest.set_state(eid, "42")

    async def render():
        resp = await rest.client.post(
            f"{rest.base_url}/api/template",
            headers=rest._headers(),
            json={"template": "{{ states('ENTITY') }}".replace("ENTITY", eid)},
        )
        return resp.text

    results = await asyncio.gather(*[render() for _ in range(5)])
    assert all(r == "42" for r in results)
