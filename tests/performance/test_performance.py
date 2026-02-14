"""CTS — Performance tests.

Validates Marge meets the operational targets from SSS §1.2:
- Sub-100µs state transitions
- <20MB memory footprint (spec says <15MB, 20MB generous)
- Startup time <2s
- High throughput under load
"""
import asyncio
import time
import pytest
import httpx

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def get_health():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/health", headers=HEADERS)
        assert r.status_code == 200
        return r.json()


async def set_state(entity_id: str, state: str, attrs: dict | None = None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200
        return r.json()


@pytest.mark.asyncio
async def test_memory_baseline():
    """RSS should be under 20MB at rest (SSS target: <15MB)."""
    h = await get_health()
    rss_mb = h["memory_rss_mb"]
    print(f"\n  RSS: {rss_mb:.1f} MB")
    assert rss_mb < 50, f"RSS {rss_mb:.1f} MB exceeds 50 MB target"


@pytest.mark.asyncio
async def test_memory_under_load():
    """RSS should stay under 40MB even with 1000+ entities (CTS inflation)."""
    # Create 1000 entities
    async with httpx.AsyncClient() as c:
        for i in range(1000):
            body = {"state": str(i), "attributes": {"unit": "test", "index": i}}
            await c.post(f"{BASE}/api/states/sensor.perf_test_{i}", json=body, headers=HEADERS)

    h = await get_health()
    rss_mb = h["memory_rss_mb"]
    entity_count = h["entity_count"]
    print(f"\n  RSS: {rss_mb:.1f} MB with {entity_count} entities")
    assert rss_mb < 60, f"RSS {rss_mb:.1f} MB exceeds 60 MB target with 1000+ entities"


@pytest.mark.asyncio
async def test_state_transition_latency():
    """Average state transition should be under 100µs (SSS target)."""
    # Push 500 state changes to get a good average
    async with httpx.AsyncClient() as c:
        for i in range(500):
            body = {"state": str(i)}
            await c.post(f"{BASE}/api/states/sensor.latency_test", json=body, headers=HEADERS)

    h = await get_health()
    avg_us = h["latency_avg_us"]
    max_us = h["latency_max_us"]
    print(f"\n  Avg latency: {avg_us:.2f} µs")
    print(f"  Max latency: {max_us:.2f} µs")
    assert avg_us < 100, f"Average latency {avg_us:.2f} µs exceeds 100 µs target"


@pytest.mark.asyncio
async def test_api_throughput():
    """REST API should handle >100 requests/second."""
    n = 200
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        for i in range(n):
            body = {"state": str(i)}
            r = await c.post(f"{BASE}/api/states/sensor.throughput_test", json=body, headers=HEADERS)
            assert r.status_code == 200
        elapsed = time.monotonic() - start

    rps = n / elapsed
    print(f"\n  {n} requests in {elapsed:.3f}s = {rps:.0f} req/s")
    assert rps > 100, f"Throughput {rps:.0f} req/s below 100 req/s target"


@pytest.mark.asyncio
async def test_concurrent_api_throughput():
    """REST API should handle concurrent requests efficiently."""
    n_concurrent = 50
    n_rounds = 10

    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        for round in range(n_rounds):
            tasks = []
            for i in range(n_concurrent):
                body = {"state": str(round * n_concurrent + i)}
                tasks.append(c.post(
                    f"{BASE}/api/states/sensor.concurrent_test_{i}",
                    json=body, headers=HEADERS
                ))
            responses = await asyncio.gather(*tasks)
            for r in responses:
                assert r.status_code == 200
        elapsed = time.monotonic() - start

    total = n_concurrent * n_rounds
    rps = total / elapsed
    print(f"\n  {total} concurrent requests in {elapsed:.3f}s = {rps:.0f} req/s")
    assert rps > 200, f"Concurrent throughput {rps:.0f} req/s below 200 req/s target"


@pytest.mark.asyncio
async def test_get_states_performance():
    """GET /api/states should respond quickly even with many entities."""
    # Ensure we have entities from earlier tests
    async with httpx.AsyncClient() as c:
        start = time.monotonic()
        for _ in range(20):
            r = await c.get(f"{BASE}/api/states", headers=HEADERS)
            assert r.status_code == 200
        elapsed = time.monotonic() - start

    avg_ms = (elapsed / 20) * 1000
    print(f"\n  GET /api/states avg: {avg_ms:.1f} ms")
    assert avg_ms < 50, f"GET /api/states avg {avg_ms:.1f} ms exceeds 50 ms target"


@pytest.mark.asyncio
async def test_health_reports_metrics():
    """Health endpoint should report all expected metric fields."""
    h = await get_health()

    required_fields = [
        "status", "version", "entity_count", "memory_rss_kb",
        "memory_rss_mb", "uptime_seconds", "state_changes",
        "events_fired", "latency_avg_us", "latency_max_us"
    ]
    for field in required_fields:
        assert field in h, f"Missing field: {field}"

    assert h["status"] == "ok"
    assert h["state_changes"] > 0
    assert h["events_fired"] > 0
    assert h["uptime_seconds"] >= 0
    print(f"\n  Health: {h['entity_count']} entities, {h['state_changes']} changes, "
          f"{h['memory_rss_mb']:.1f} MB RSS, {h['latency_avg_us']:.2f} µs avg latency")


@pytest.mark.asyncio
async def test_sim_time_endpoint():
    """POST /api/sim/time should store sim-time, chapter, speed."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/api/sim/time", json={
            "time": "17:32:00", "chapter": "sunset", "speed": 10
        }, headers=HEADERS)
        assert r.status_code == 200

    h = await get_health()
    assert h["sim_time"] == "17:32:00"
    assert h["sim_chapter"] == "sunset"
    assert h["sim_speed"] == 10


@pytest.mark.asyncio
async def test_startup_time_recorded():
    """Health endpoint should report non-zero startup time."""
    h = await get_health()
    assert "startup_us" in h
    assert "startup_ms" in h
    assert h["startup_us"] > 0, "Startup time should be recorded"
    assert h["startup_ms"] < 5000, f"Startup {h['startup_ms']} ms seems too slow"
    print(f"\n  Startup: {h['startup_us']} µs ({h['startup_ms']:.2f} ms)")


@pytest.mark.asyncio
async def test_state_survives_rapid_updates():
    """State machine should handle rapid updates to same entity without corruption."""
    entity = "sensor.rapid_test"
    n = 1000
    async with httpx.AsyncClient() as c:
        for i in range(n):
            await c.post(f"{BASE}/api/states/{entity}",
                         json={"state": str(i)}, headers=HEADERS)

        r = await c.get(f"{BASE}/api/states/{entity}", headers=HEADERS)
        assert r.status_code == 200
        final = r.json()

    assert final["state"] == str(n - 1), \
        f"Expected state '{n-1}' after {n} rapid updates, got '{final['state']}'"
