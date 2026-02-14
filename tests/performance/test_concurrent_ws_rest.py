"""
CTS -- Concurrent WS and REST Operations Tests

Tests concurrent WebSocket and REST operations to verify
thread safety: parallel state sets, concurrent WS subscriptions,
mixed REST/WS operations.
"""

import asyncio
import uuid
import pytest
import httpx

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}

pytestmark = pytest.mark.asyncio


async def test_parallel_state_sets_10(rest):
    """10 parallel state sets all succeed."""
    tag = uuid.uuid4().hex[:8]

    async def set_one(i):
        await rest.set_state(f"sensor.par_{tag}_{i}", str(i))

    await asyncio.gather(*[set_one(i) for i in range(10)])

    for i in range(10):
        state = await rest.get_state(f"sensor.par_{tag}_{i}")
        assert state is not None
        assert state["state"] == str(i)


async def test_parallel_service_calls(rest):
    """10 parallel service calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.par_svc_{tag}_{i}" for i in range(10)]

    for eid in entities:
        await rest.set_state(eid, "off")

    async def turn_on(eid):
        await rest.call_service("light", "turn_on", {"entity_id": eid})

    await asyncio.gather(*[turn_on(eid) for eid in entities])

    for eid in entities:
        assert (await rest.get_state(eid))["state"] == "on"


async def test_concurrent_get_states():
    """5 concurrent GET /api/states requests all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.get(f"{BASE}/api/states", headers=HEADERS)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200
        assert isinstance(r.json(), list)


async def test_concurrent_health_checks():
    """10 concurrent health checks complete quickly."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.get(f"{BASE}/api/health", headers=HEADERS)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200


async def test_concurrent_search_requests():
    """5 concurrent search requests all return valid results."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.get(f"{BASE}/api/states/search", params={"domain": "light"}, headers=HEADERS)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

    for r in results:
        assert r.status_code == 200


async def test_mixed_read_write_concurrent(rest):
    """Concurrent reads and writes don't interfere."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mixed_{tag}"
    await rest.set_state(eid, "initial")

    async def writer():
        for i in range(5):
            await rest.set_state(eid, f"write_{i}")
            await asyncio.sleep(0.01)

    async def reader():
        for _ in range(5):
            state = await rest.get_state(eid)
            assert state is not None
            await asyncio.sleep(0.01)

    await asyncio.gather(writer(), reader())

    # Final state should be the last written value
    state = await rest.get_state(eid)
    assert state["state"] == "write_4"


async def test_concurrent_template_renders():
    """5 concurrent template renders all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/template",
                json={"template": f"{{{{ {i} + {i} }}}}"},
                headers=HEADERS,
            )
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

    for i, r in enumerate(results):
        assert r.status_code == 200
        assert str(i * 2) in r.text
