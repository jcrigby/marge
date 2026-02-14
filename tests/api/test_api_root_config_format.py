"""
CTS -- API Root and Config Endpoint Format Tests

Tests GET /api/ (status) and GET /api/config (system configuration)
response formats match HA-compatible structure.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/ ─────────────────────────────────────────────

async def test_api_root_returns_200(rest):
    """GET /api/ returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_api_root_has_message(rest):
    """GET /api/ returns JSON with 'message' field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


async def test_api_root_message_content(rest):
    """GET /api/ message says 'API running.'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.json()["message"] == "API running."


# ── GET /api/config ────────────────────────────────────────

async def test_config_returns_200(rest):
    """GET /api/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_config_has_location_name(rest):
    """Config includes location_name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "location_name" in data
    assert isinstance(data["location_name"], str)


async def test_config_has_coordinates(rest):
    """Config includes latitude and longitude."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "latitude" in data
    assert "longitude" in data
    assert isinstance(data["latitude"], (int, float))
    assert isinstance(data["longitude"], (int, float))


async def test_config_has_elevation(rest):
    """Config includes elevation field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "elevation" in data
    assert isinstance(data["elevation"], (int, float))


async def test_config_has_unit_system(rest):
    """Config includes unit_system with HA-compatible fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "unit_system" in data
    us = data["unit_system"]
    assert "length" in us
    assert "mass" in us
    assert "temperature" in us
    assert "volume" in us


async def test_config_has_time_zone(rest):
    """Config includes time_zone field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "time_zone" in data
    assert "/" in data["time_zone"]  # e.g., "America/Denver"


async def test_config_has_version(rest):
    """Config includes version field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "version" in data
    assert isinstance(data["version"], str)


async def test_config_has_state(rest):
    """Config includes state field with value 'RUNNING'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data.get("state") == "RUNNING"


async def test_config_is_json(rest):
    """Config response is application/json."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert "application/json" in resp.headers.get("content-type", "")
