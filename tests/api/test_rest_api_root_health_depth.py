"""
CTS -- REST API Root & Health Depth Tests

Tests GET /api/ status, /api/health, /api/config, and
/api/error_log endpoints for response format and content.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── API Status ──────────────────────────────────────────

async def test_api_root_returns_200(rest):
    """GET /api/ returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_root_returns_json(rest):
    """GET /api/ returns JSON."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, dict)


async def test_api_root_has_message(rest):
    """GET /api/ response includes message field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "message" in data


# ── Health ──────────────────────────────────────────────

async def test_health_returns_200(rest):
    """GET /api/health returns 200."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200


async def test_health_returns_json(rest):
    """GET /api/health returns JSON."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert isinstance(data, dict)


# ── Config ──────────────────────────────────────────────

async def test_config_returns_200(rest):
    """GET /api/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_config_has_version(rest):
    """GET /api/config response includes version."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data


async def test_config_has_location(rest):
    """GET /api/config response includes latitude/longitude."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "latitude" in data
    assert "longitude" in data


# ── Error Log ───────────────────────────────────────────

async def test_error_log_returns_200(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Check Config ────────────────────────────────────────

async def test_check_config_returns_200(rest):
    """POST /api/config/core/check_config returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
