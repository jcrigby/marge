"""
CTS -- Configuration & Miscellaneous Endpoint Tests

Tests /api/config, /api/error_log, /api/config/core/check_config,
/api/health fields, /api/config/automation/reload, /metrics,
and device registry REST endpoints.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Config Endpoint ───────────────────────────────────────

async def test_config_has_state(rest):
    """GET /api/config includes state field."""
    config = await rest.get_config()
    assert "state" in config
    assert config["state"] == "RUNNING"


async def test_config_has_location(rest):
    """GET /api/config includes location fields."""
    config = await rest.get_config()
    assert "latitude" in config
    assert "longitude" in config
    assert isinstance(config["latitude"], (int, float))


async def test_config_has_unit_system(rest):
    """GET /api/config includes unit_system."""
    config = await rest.get_config()
    assert "unit_system" in config


async def test_config_has_version(rest):
    """GET /api/config includes version string."""
    config = await rest.get_config()
    assert "version" in config
    assert isinstance(config["version"], str)


# ── Error Log ─────────────────────────────────────────────

async def test_error_log_endpoint(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Check Config ──────────────────────────────────────────

async def test_check_config(rest):
    """POST /api/config/core/check_config returns valid result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body


# ── Health Endpoint ───────────────────────────────────────

@pytest.mark.marge_only
async def test_health_has_status(rest):
    """GET /api/health includes status field."""
    health = await rest.get_health()
    assert "status" in health
    assert health["status"] == "ok"


@pytest.mark.marge_only
async def test_health_has_entity_count(rest):
    """GET /api/health includes entity_count."""
    health = await rest.get_health()
    assert "entity_count" in health
    assert isinstance(health["entity_count"], int)
    assert health["entity_count"] >= 0


@pytest.mark.marge_only
async def test_health_has_uptime(rest):
    """GET /api/health includes uptime_seconds."""
    health = await rest.get_health()
    assert "uptime_seconds" in health
    assert health["uptime_seconds"] >= 0


@pytest.mark.marge_only
async def test_health_has_memory(rest):
    """GET /api/health includes memory_rss_kb."""
    health = await rest.get_health()
    assert "memory_rss_kb" in health
    assert health["memory_rss_kb"] > 0


# ── Automation Reload ─────────────────────────────────────

@pytest.mark.marge_only
async def test_automation_reload_endpoint(rest):
    """POST /api/config/automation/reload returns success."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Prometheus Metrics ────────────────────────────────────

@pytest.mark.marge_only
async def test_prometheus_metrics_endpoint(rest):
    """GET /metrics returns Prometheus-format text."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Should contain at least one metric line
    assert "marge_" in text or "entity" in text or "uptime" in text


# ── Device Registry ───────────────────────────────────────

@pytest.mark.marge_only
async def test_devices_list(rest):
    """GET /api/devices returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.marge_only
async def test_device_create(rest):
    """POST /api/devices creates a new device."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": "cts_test_device",
            "name": "CTS Device",
            "manufacturer": "Test Co",
            "model": "T-1000",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify it appears
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    ids = [d["device_id"] for d in resp.json()]
    assert "cts_test_device" in ids

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/devices/cts_test_device",
        headers=rest._headers(),
    )


@pytest.mark.marge_only
async def test_device_delete(rest):
    """DELETE /api/devices/{id} removes a device."""
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": "cts_del_device",
            "name": "Delete Device",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/devices/cts_del_device",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify gone
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    ids = [d["device_id"] for d in resp.json()]
    assert "cts_del_device" not in ids


@pytest.mark.marge_only
async def test_device_entity_assignment(rest):
    """POST /api/devices/{id}/entities/{eid} assigns entity to device."""
    # Create device and entity
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": "cts_assign_device",
            "name": "Assign Device",
        },
        headers=rest._headers(),
    )
    await rest.set_state("sensor.device_assign_test", "42")

    # Assign
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/cts_assign_device/entities/sensor.device_assign_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/devices/cts_assign_device",
        headers=rest._headers(),
    )


# ── Merged from depth: API Root ──────────────────────────

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


# ── Merged from depth: Config Field Depth ────────────────

async def test_config_has_location_name(rest):
    """Config has location_name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "location_name" in data
    assert len(data["location_name"]) > 0


async def test_config_has_coordinates_in_range(rest):
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


async def test_config_has_unit_system_fields(rest):
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


# ── Merged from depth: Health Field Depth ────────────────

@pytest.mark.marge_only
async def test_health_has_version(rest):
    """Health endpoint has version field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data


@pytest.mark.marge_only
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


@pytest.mark.marge_only
async def test_health_has_latency_fields(rest):
    """Health endpoint has latency_avg_us and latency_max_us."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "latency_avg_us" in data
    assert "latency_max_us" in data


@pytest.mark.marge_only
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


@pytest.mark.marge_only
async def test_health_has_counters(rest):
    """Health endpoint has state_changes and events_fired."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "state_changes" in data
    assert "events_fired" in data


@pytest.mark.marge_only
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


# -- from test_extended_api.py --

async def test_health_startup_under_5ms(rest):
    """Marge starts up in under 5ms."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["startup_ms"] < 5.0, f"Startup took {data['startup_ms']}ms"
