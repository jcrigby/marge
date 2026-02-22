"""
CTS -- Latency and Throughput Performance Tests

Tests state change throughput, REST API latency under load,
and concurrent service call performance. All assertions use
generous bounds to avoid flaky CI failures.
"""

import asyncio
import time
import uuid
import pytest
import httpx

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}

pytestmark = pytest.mark.asyncio


async def test_state_set_latency():
    """Single state set completes in under 50ms."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.post(
            f"{BASE}/api/states/sensor.lat_{tag}",
            json={"state": "42"},
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.05  # 50ms


async def test_state_get_latency():
    """Single state GET completes in under 50ms."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/sensor.getlat_{tag}",
            json={"state": "val"},
            headers=HEADERS,
        )
        start = time.monotonic()
        r = await c.get(
            f"{BASE}/api/states/sensor.getlat_{tag}",
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.05


async def test_sequential_state_throughput():
    """100 sequential state sets complete in under 5s."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        for i in range(100):
            r = await c.post(
                f"{BASE}/api/states/sensor.seq_{tag}",
                json={"state": str(i)},
                headers=HEADERS,
            )
            assert r.status_code in (200, 201)
        elapsed = time.monotonic() - start
    assert elapsed < 5.0  # 20+ ops/sec


async def test_concurrent_state_throughput():
    """50 concurrent state sets complete in under 3s."""
    tag = uuid.uuid4().hex[:8]

    async def set_state(client, i):
        r = await client.post(
            f"{BASE}/api/states/sensor.conc_{tag}_{i}",
            json={"state": str(i)},
            headers=HEADERS,
        )
        return r.status_code

    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        tasks = [set_state(c, i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start

    assert all(r == 200 for r in results)
    assert elapsed < 3.0


async def test_service_call_latency():
    """Service call completes in under 100ms."""
    tag = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/light.svclat_{tag}",
            json={"state": "off"},
            headers=HEADERS,
        )
        start = time.monotonic()
        r = await c.post(
            f"{BASE}/api/services/light/turn_on",
            json={"entity_id": f"light.svclat_{tag}"},
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.1


async def test_health_endpoint_latency():
    """Health check completes in under 20ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.get(f"{BASE}/api/health", headers=HEADERS)
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.02


async def test_config_endpoint_latency():
    """Config endpoint completes in under 20ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.get(f"{BASE}/api/config", headers=HEADERS)
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.02


async def test_search_latency():
    """Search endpoint completes in under 100ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.get(
            f"{BASE}/api/states/search",
            params={"domain": "light"},
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.1


async def test_template_render_latency():
    """Template render completes in under 50ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.post(
            f"{BASE}/api/template",
            json={"template": "{{ 1 + 2 + 3 + 4 + 5 }}"},
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code in (200, 201)
    assert elapsed < 0.05
