"""
CTS -- Config Endpoints Depth Tests

Tests GET /api/config, GET /api/, GET /api/health for all expected
fields, value ranges, and format compliance.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_api_root_status(rest):
    """GET /api/ returns API running message."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "running" in data["message"].lower() or "api" in data["message"].lower()


async def test_config_has_location_name(rest):
    """Config has location_name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "location_name" in data
    assert len(data["location_name"]) > 0


async def test_config_has_coordinates(rest):
    """Config has latitude and longitude in valid ranges."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert -90 <= data["latitude"] <= 90
    assert -180 <= data["longitude"] <= 180


async def test_config_has_elevation(rest):
    """Config has elevation field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "elevation" in data
    assert isinstance(data["elevation"], (int, float))


async def test_config_has_unit_system(rest):
    """Config has unit_system with expected fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    us = data["unit_system"]
    assert "length" in us
    assert "mass" in us
    assert "temperature" in us
    assert "volume" in us


async def test_config_has_timezone(rest):
    """Config has time_zone field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "time_zone" in data
    assert "/" in data["time_zone"]  # e.g., "America/New_York"


async def test_config_has_version(rest):
    """Config has version field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data
    assert len(data["version"]) > 0


async def test_config_state_running(rest):
    """Config state is RUNNING."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["state"] == "RUNNING"


async def test_health_has_status_ok(rest):
    """Health endpoint reports status ok."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_has_version(rest):
    """Health endpoint has version field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data


async def test_health_has_entity_count(rest):
    """Health endpoint has entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "entity_count" in data
    assert data["entity_count"] >= 0


async def test_health_has_memory_fields(rest):
    """Health endpoint has memory_rss_kb and memory_rss_mb."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "memory_rss_kb" in data
    assert "memory_rss_mb" in data
    assert data["memory_rss_mb"] > 0


async def test_health_has_latency_fields(rest):
    """Health endpoint has latency_avg_us and latency_max_us."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "latency_avg_us" in data
    assert "latency_max_us" in data


async def test_health_has_uptime(rest):
    """Health endpoint has uptime_seconds."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


async def test_health_has_startup_time(rest):
    """Health endpoint has startup_us and startup_ms."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "startup_us" in data
    assert "startup_ms" in data
    assert data["startup_us"] > 0


async def test_health_has_counters(rest):
    """Health endpoint has state_changes and events_fired."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "state_changes" in data
    assert "events_fired" in data


async def test_health_has_sim_fields(rest):
    """Health endpoint has sim_time/sim_chapter/sim_speed after sim/time call."""
    # Set sim time first
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "12:00:00", "chapter": "noon", "speed": 5},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "sim_time" in data
    assert "sim_chapter" in data
    assert "sim_speed" in data


async def test_ws_config_matches_rest(ws, rest):
    """WS get_config returns same config as REST."""
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    rest_config = rest_resp.json()

    ws_resp = await ws.send_command("get_config")
    ws_config = ws_resp["result"]

    assert rest_config["latitude"] == ws_config["latitude"]
    assert rest_config["longitude"] == ws_config["longitude"]
    assert rest_config["version"] == ws_config["version"]
