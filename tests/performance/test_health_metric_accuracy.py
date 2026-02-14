"""
CTS -- Health Metric Accuracy Tests

Tests that /api/health metrics are accurate: state_changes increments,
entity_count reflects actual entities, uptime increases, and
startup metrics are present and sensible.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_state_changes_increments_on_set(rest):
    """state_changes metric increments after setting state."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    count1 = resp1.json()["state_changes"]

    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.metric_{tag}", "val")

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    count2 = resp2.json()["state_changes"]
    assert count2 > count1


async def test_entity_count_increases_on_create(rest):
    """entity_count increases when new entity is created."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    count1 = resp1.json()["entity_count"]

    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.metric_ec_{tag}", "val")

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    count2 = resp2.json()["entity_count"]
    assert count2 > count1


async def test_uptime_increases(rest):
    """uptime_seconds increases over time."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    uptime1 = resp1.json()["uptime_seconds"]

    await asyncio.sleep(1.1)

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    uptime2 = resp2.json()["uptime_seconds"]
    assert uptime2 > uptime1


async def test_health_has_status_ok(rest):
    """Health status field is 'ok'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    assert resp.json()["status"] == "ok"


async def test_health_has_version(rest):
    """Health has version field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data
    assert len(data["version"]) > 0


async def test_health_has_startup_us(rest):
    """Health has startup_us metric."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "startup_us" in data
    assert data["startup_us"] >= 0


async def test_health_has_startup_ms(rest):
    """Health has startup_ms metric."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "startup_ms" in data
    assert data["startup_ms"] >= 0


async def test_health_has_latency_metrics(rest):
    """Health has latency_avg_us and latency_max_us."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "latency_avg_us" in data
    assert "latency_max_us" in data
    assert data["latency_avg_us"] >= 0
    assert data["latency_max_us"] >= 0


async def test_health_has_ws_connections(rest):
    """Health has ws_connections count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "ws_connections" in data
    assert data["ws_connections"] >= 0


async def test_health_has_memory_metrics(rest):
    """Health has memory_rss_kb and memory_rss_mb."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "memory_rss_kb" in data
    assert "memory_rss_mb" in data
    assert data["memory_rss_kb"] > 0


async def test_health_rss_mb_matches_kb(rest):
    """memory_rss_mb is approximately memory_rss_kb / 1024."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    expected_mb = data["memory_rss_kb"] / 1024.0
    assert abs(data["memory_rss_mb"] - expected_mb) < 1.0


async def test_health_events_fired_nonnegative(rest):
    """events_fired metric is non-negative."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "events_fired" in data
    assert data["events_fired"] >= 0


async def test_health_sim_fields_present(rest):
    """Health has sim_time, sim_chapter, sim_speed fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "sim_time" in data
    assert "sim_chapter" in data
    assert "sim_speed" in data
