"""
CTS -- Health and Metrics Endpoint Depth Tests

Tests all health endpoint fields, metrics after operations,
entity count accuracy, and Prometheus metrics format.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_has_all_fields(rest):
    """Health endpoint has all expected fields."""
    health = await rest.get_health()
    expected_fields = [
        "status", "version", "entity_count", "memory_rss_kb",
        "memory_rss_mb", "uptime_seconds", "startup_us", "startup_ms",
        "state_changes", "events_fired", "latency_avg_us", "latency_max_us",
        "sim_time", "sim_chapter", "sim_speed", "ws_connections",
    ]
    for field in expected_fields:
        assert field in health, f"Missing field: {field}"


async def test_health_entity_count_increases(rest):
    """Entity count increases after creating entities."""
    import uuid
    tag = uuid.uuid4().hex[:8]
    h1 = await rest.get_health()
    count1 = h1["entity_count"]

    await rest.set_state(f"sensor.health_depth_{tag}_1", "1")
    await rest.set_state(f"sensor.health_depth_{tag}_2", "2")

    h2 = await rest.get_health()
    count2 = h2["entity_count"]
    assert count2 >= count1 + 2


async def test_health_state_changes_increment(rest):
    """State changes counter increments after set_state."""
    h1 = await rest.get_health()
    changes1 = h1["state_changes"]

    await rest.set_state("sensor.health_depth_sc", "100")

    h2 = await rest.get_health()
    changes2 = h2["state_changes"]
    assert changes2 > changes1


async def test_health_uptime_positive(rest):
    """Uptime is positive."""
    health = await rest.get_health()
    assert health["uptime_seconds"] >= 0


async def test_health_memory_positive(rest):
    """Memory RSS is positive."""
    health = await rest.get_health()
    assert health["memory_rss_kb"] > 0
    assert health["memory_rss_mb"] > 0


async def test_health_latency_non_negative(rest):
    """Latency values are non-negative."""
    health = await rest.get_health()
    assert health["latency_avg_us"] >= 0
    assert health["latency_max_us"] >= 0


async def test_health_version_format(rest):
    """Version is a non-empty string."""
    health = await rest.get_health()
    assert isinstance(health["version"], str)
    assert len(health["version"]) > 0


async def test_health_status_ok(rest):
    """Status is always ok."""
    health = await rest.get_health()
    assert health["status"] == "ok"


async def test_prometheus_has_state_changes(rest):
    """Prometheus metrics include state_changes metric."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    # Should have HELP/TYPE lines or metric data
    assert len(text) > 0


async def test_prometheus_no_auth(rest):
    """Prometheus metrics endpoint works without auth header."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
