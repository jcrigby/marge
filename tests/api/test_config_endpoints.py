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

async def test_health_has_status(rest):
    """GET /api/health includes status field."""
    health = await rest.get_health()
    assert "status" in health
    assert health["status"] == "ok"


async def test_health_has_entity_count(rest):
    """GET /api/health includes entity_count."""
    health = await rest.get_health()
    assert "entity_count" in health
    assert isinstance(health["entity_count"], int)
    assert health["entity_count"] >= 0


async def test_health_has_uptime(rest):
    """GET /api/health includes uptime_seconds."""
    health = await rest.get_health()
    assert "uptime_seconds" in health
    assert health["uptime_seconds"] >= 0


async def test_health_has_memory(rest):
    """GET /api/health includes memory_rss_kb."""
    health = await rest.get_health()
    assert "memory_rss_kb" in health
    assert health["memory_rss_kb"] > 0


# ── Automation Reload ─────────────────────────────────────

async def test_automation_reload_endpoint(rest):
    """POST /api/config/automation/reload returns success."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Prometheus Metrics ────────────────────────────────────

async def test_prometheus_metrics_endpoint(rest):
    """GET /metrics returns Prometheus-format text."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Should contain at least one metric line
    assert "marge_" in text or "entity" in text or "uptime" in text


# ── Device Registry ───────────────────────────────────────

async def test_devices_list(rest):
    """GET /api/devices returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


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
