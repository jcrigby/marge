"""
CTS -- API Root, Health, and Config Endpoint Depth Tests

Tests GET /api/ status, GET /api/config field completeness,
GET /api/health field completeness and value types, ensuring
HA-compatible response formats.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── API Root ──────────────────────────────────────────────

async def test_api_root_returns_200(rest):
    """GET /api/ returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_root_has_message(rest):
    """GET /api/ response has message field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "message" in data
    assert "API" in data["message"]


# ── Config Endpoint Fields ────────────────────────────────

async def test_config_location_name(rest):
    """Config has location_name string."""
    config = await rest.get_config()
    assert isinstance(config["location_name"], str)
    assert len(config["location_name"]) > 0


async def test_config_latitude_is_numeric(rest):
    """Config latitude is numeric."""
    config = await rest.get_config()
    assert isinstance(config["latitude"], (int, float))


async def test_config_longitude_is_numeric(rest):
    """Config longitude is numeric."""
    config = await rest.get_config()
    assert isinstance(config["longitude"], (int, float))


async def test_config_elevation_present(rest):
    """Config has elevation field."""
    config = await rest.get_config()
    assert "elevation" in config
    assert isinstance(config["elevation"], (int, float))


async def test_config_unit_system_has_temperature(rest):
    """Config unit_system has temperature field."""
    config = await rest.get_config()
    us = config["unit_system"]
    assert "temperature" in us


async def test_config_unit_system_has_length(rest):
    """Config unit_system has length field."""
    config = await rest.get_config()
    us = config["unit_system"]
    assert "length" in us


async def test_config_unit_system_has_mass(rest):
    """Config unit_system has mass field."""
    config = await rest.get_config()
    us = config["unit_system"]
    assert "mass" in us


async def test_config_unit_system_has_volume(rest):
    """Config unit_system has volume field."""
    config = await rest.get_config()
    us = config["unit_system"]
    assert "volume" in us


async def test_config_time_zone(rest):
    """Config has time_zone string."""
    config = await rest.get_config()
    assert "time_zone" in config
    assert isinstance(config["time_zone"], str)


async def test_config_version_string(rest):
    """Config version is a non-empty string."""
    config = await rest.get_config()
    assert isinstance(config["version"], str)
    assert len(config["version"]) > 0


async def test_config_state_running(rest):
    """Config state is RUNNING."""
    config = await rest.get_config()
    assert config["state"] == "RUNNING"


# ── Health Endpoint Fields ────────────────────────────────

async def test_health_status_ok(rest):
    """Health status is ok."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_version_present(rest):
    """Health response has version field."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "version" in data
    assert isinstance(data["version"], str)


async def test_health_uptime_positive(rest):
    """Health uptime_seconds is positive."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert data["uptime_seconds"] > 0


async def test_health_entity_count_type(rest):
    """Health entity_count is integer."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert isinstance(data["entity_count"], int)


async def test_health_memory_rss_kb(rest):
    """Health memory_rss_kb is positive."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert data["memory_rss_kb"] > 0


async def test_health_memory_rss_mb(rest):
    """Health memory_rss_mb is positive float."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert isinstance(data["memory_rss_mb"], (int, float))
    assert data["memory_rss_mb"] > 0


async def test_health_startup_us(rest):
    """Health startup_us is non-negative."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "startup_us" in data
    assert data["startup_us"] >= 0


async def test_health_startup_ms(rest):
    """Health startup_ms is non-negative."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "startup_ms" in data
    assert data["startup_ms"] >= 0


async def test_health_state_changes_type(rest):
    """Health state_changes is integer."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert isinstance(data["state_changes"], int)


async def test_health_events_fired(rest):
    """Health events_fired is integer."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "events_fired" in data
    assert isinstance(data["events_fired"], int)


async def test_health_latency_avg_us(rest):
    """Health latency_avg_us is numeric."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "latency_avg_us" in data
    assert isinstance(data["latency_avg_us"], (int, float))


async def test_health_latency_max_us(rest):
    """Health latency_max_us is numeric."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "latency_max_us" in data
    assert isinstance(data["latency_max_us"], (int, float))


async def test_health_ws_connections(rest):
    """Health ws_connections is integer."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "ws_connections" in data
    assert isinstance(data["ws_connections"], int)


async def test_health_no_auth_required(rest):
    """Health endpoint works without auth header."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
