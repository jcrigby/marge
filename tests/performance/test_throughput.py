"""
CTS -- Throughput and Performance Tests

Tests state machine throughput, API response times,
and concurrent operation handling.
"""

import asyncio
import time

import httpx
import pytest

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}

pytestmark = pytest.mark.asyncio


async def test_state_set_throughput():
    """Can set 100 entities in under 5 seconds."""
    start = time.monotonic()
    async with httpx.AsyncClient() as c:
        for i in range(100):
            body = {"state": str(i), "attributes": {"index": i}}
            r = await c.post(
                f"{BASE}/api/states/sensor.throughput_test_{i}",
                json=body, headers=HEADERS,
            )
            assert r.status_code == 200
    elapsed = time.monotonic() - start
    print(f"\n  100 state sets: {elapsed:.2f}s ({100/elapsed:.0f}/sec)")
    assert elapsed < 5.0


async def test_state_get_throughput():
    """Can get 100 entity states in under 5 seconds."""
    # Create entities first
    async with httpx.AsyncClient() as c:
        for i in range(100):
            await c.post(
                f"{BASE}/api/states/sensor.get_throughput_{i}",
                json={"state": str(i)}, headers=HEADERS,
            )

    start = time.monotonic()
    async with httpx.AsyncClient() as c:
        for i in range(100):
            r = await c.get(
                f"{BASE}/api/states/sensor.get_throughput_{i}",
                headers=HEADERS,
            )
            assert r.status_code == 200
    elapsed = time.monotonic() - start
    print(f"\n  100 state gets: {elapsed:.2f}s ({100/elapsed:.0f}/sec)")
    assert elapsed < 5.0


async def test_concurrent_state_sets():
    """50 concurrent state sets all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/states/sensor.conc_perf_{i}",
                json={"state": str(i)}, headers=HEADERS,
            )
            for i in range(50)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


async def test_health_endpoint_fast():
    """Health endpoint responds in under 100ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.get(f"{BASE}/api/health")
        elapsed = time.monotonic() - start
    assert r.status_code == 200
    assert elapsed < 0.1, f"Health took {elapsed:.3f}s"


async def test_service_call_throughput():
    """10 service calls complete in under 2 seconds."""
    async with httpx.AsyncClient() as c:
        # Set up entities
        for i in range(10):
            await c.post(
                f"{BASE}/api/states/light.svc_throughput_{i}",
                json={"state": "off"}, headers=HEADERS,
            )

    start = time.monotonic()
    async with httpx.AsyncClient() as c:
        for i in range(10):
            r = await c.post(
                f"{BASE}/api/services/light/turn_on",
                json={"entity_id": f"light.svc_throughput_{i}"},
                headers=HEADERS,
            )
            assert r.status_code == 200
    elapsed = time.monotonic() - start
    print(f"\n  10 service calls: {elapsed:.2f}s ({10/elapsed:.0f}/sec)")
    assert elapsed < 2.0


async def test_template_render_throughput():
    """20 template renders complete in under 2 seconds."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        for i in range(20):
            r = await c.post(
                f"{BASE}/api/template",
                json={"template": f"{{{{ {i} * {i} }}}}"},
                headers=HEADERS,
            )
            assert r.status_code == 200
            assert r.text.strip() == str(i * i)
        elapsed = time.monotonic() - start
    print(f"\n  20 template renders: {elapsed:.2f}s ({20/elapsed:.0f}/sec)")
    assert elapsed < 2.0


async def test_search_throughput():
    """Search with filters responds in under 500ms."""
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        r = await c.get(
            f"{BASE}/api/states/search?domain=sensor&state=42",
            headers=HEADERS,
        )
        elapsed = time.monotonic() - start
    assert r.status_code == 200
    assert elapsed < 0.5, f"Search took {elapsed:.3f}s"
