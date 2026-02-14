"""
CTS -- Concurrent Operation and Race Condition Tests

Tests concurrent state operations, parallel service calls,
simultaneous WS connections, and mixed REST/MQTT operations.
"""

import asyncio
import time

import httpx
import pytest

pytestmark = pytest.mark.asyncio

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


# ── Concurrent State Writes ──────────────────────────────

async def test_concurrent_writes_same_entity():
    """10 concurrent writes to same entity all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/states/sensor.conc_same",
                json={"state": str(i)},
                headers=HEADERS,
            )
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


async def test_concurrent_writes_different_entities():
    """50 concurrent writes to different entities all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/states/sensor.conc_diff_{i}",
                json={"state": str(i)},
                headers=HEADERS,
            )
            for i in range(50)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


async def test_concurrent_read_write():
    """Concurrent reads and writes don't crash."""
    async with httpx.AsyncClient() as c:
        # Pre-create entity
        await c.post(
            f"{BASE}/api/states/sensor.conc_rw",
            json={"state": "init"},
            headers=HEADERS,
        )

        writes = [
            c.post(
                f"{BASE}/api/states/sensor.conc_rw",
                json={"state": f"write_{i}"},
                headers=HEADERS,
            )
            for i in range(10)
        ]
        reads = [
            c.get(f"{BASE}/api/states/sensor.conc_rw", headers=HEADERS)
            for _ in range(10)
        ]
        results = await asyncio.gather(*(writes + reads))
    assert all(r.status_code == 200 for r in results)


# ── Concurrent Service Calls ─────────────────────────────

async def test_concurrent_service_calls():
    """20 concurrent service calls to different entities succeed."""
    async with httpx.AsyncClient() as c:
        # Pre-create entities
        for i in range(20):
            await c.post(
                f"{BASE}/api/states/light.conc_svc_{i}",
                json={"state": "off"},
                headers=HEADERS,
            )

        tasks = [
            c.post(
                f"{BASE}/api/services/light/turn_on",
                json={"entity_id": f"light.conc_svc_{i}"},
                headers=HEADERS,
            )
            for i in range(20)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


async def test_concurrent_toggle_same_entity():
    """Rapid toggles of same entity all succeed."""
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/light.conc_toggle",
            json={"state": "off"},
            headers=HEADERS,
        )

        tasks = [
            c.post(
                f"{BASE}/api/services/light/toggle",
                json={"entity_id": "light.conc_toggle"},
                headers=HEADERS,
            )
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


# ── Concurrent Template Rendering ────────────────────────

async def test_concurrent_template_renders():
    """20 concurrent template renders all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/template",
                json={"template": f"{{{{ {i} * {i} }}}}"},
                headers=HEADERS,
            )
            for i in range(20)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)
    for i, r in enumerate(results):
        assert r.text.strip() == str(i * i)


# ── Concurrent Search Queries ────────────────────────────

async def test_concurrent_search_queries():
    """10 concurrent search queries all succeed."""
    async with httpx.AsyncClient() as c:
        tasks = [
            c.get(
                f"{BASE}/api/states/search?domain=sensor",
                headers=HEADERS,
            )
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


# ── Mixed Operations ────────────────────────────────────

async def test_mixed_operations_concurrent():
    """Mix of state set, get, service, search, template all concurrent."""
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/sensor.conc_mixed",
            json={"state": "0"},
            headers=HEADERS,
        )

        tasks = [
            c.post(f"{BASE}/api/states/sensor.conc_mixed_a",
                   json={"state": "1"}, headers=HEADERS),
            c.get(f"{BASE}/api/states/sensor.conc_mixed", headers=HEADERS),
            c.get(f"{BASE}/api/states/search?domain=sensor", headers=HEADERS),
            c.post(f"{BASE}/api/template",
                   json={"template": "{{ 1 + 1 }}"}, headers=HEADERS),
            c.get(f"{BASE}/api/health"),
            c.get(f"{BASE}/api/states", headers=HEADERS),
        ]
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)


# ── High Throughput Burst ────────────────────────────────

async def test_burst_100_state_sets():
    """100 concurrent state sets complete in under 5 seconds."""
    start = time.monotonic()
    async with httpx.AsyncClient() as c:
        tasks = [
            c.post(
                f"{BASE}/api/states/sensor.burst_{i}",
                json={"state": str(i)},
                headers=HEADERS,
            )
            for i in range(100)
        ]
        results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start
    assert all(r.status_code == 200 for r in results)
    assert elapsed < 5.0, f"100 concurrent sets took {elapsed:.2f}s"


# ── Delete During Read ───────────────────────────────────

async def test_delete_while_reading():
    """Delete entity while reading doesn't crash."""
    async with httpx.AsyncClient() as c:
        # Create entity
        await c.post(
            f"{BASE}/api/states/sensor.conc_del",
            json={"state": "exists"},
            headers=HEADERS,
        )

        # Concurrent reads and a delete
        reads = [
            c.get(f"{BASE}/api/states/sensor.conc_del", headers=HEADERS)
            for _ in range(5)
        ]
        delete = c.request(
            "DELETE",
            f"{BASE}/api/states/sensor.conc_del",
            headers=HEADERS,
        )
        results = await asyncio.gather(*reads, delete)
    # All should return 200 or 404 (not 500)
    assert all(r.status_code in (200, 404) for r in results)


# ── Concurrent Health Checks ────────────────────────────

async def test_concurrent_health_checks():
    """50 concurrent health checks all succeed fast."""
    start = time.monotonic()
    async with httpx.AsyncClient() as c:
        tasks = [c.get(f"{BASE}/api/health") for _ in range(50)]
        results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start
    assert all(r.status_code == 200 for r in results)
    assert elapsed < 2.0, f"50 health checks took {elapsed:.2f}s"
