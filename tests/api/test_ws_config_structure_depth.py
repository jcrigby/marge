"""
CTS -- WS Config Structure Depth Tests

Tests WebSocket get_config response structure: required fields,
version info, location data, unit system, and config entries.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Get Config ──────────────────────────────────────────

async def test_ws_get_config_success(ws):
    """get_config returns success."""
    result = await ws.send_command("get_config")
    assert result["success"] is True


async def test_ws_get_config_has_version(ws):
    """get_config result includes version."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "version" in cfg


async def test_ws_get_config_has_location(ws):
    """get_config result includes location fields."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "latitude" in cfg
    assert "longitude" in cfg


async def test_ws_get_config_has_unit_system(ws):
    """get_config result includes unit_system."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "unit_system" in cfg


async def test_ws_get_config_has_time_zone(ws):
    """get_config result includes time_zone."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "time_zone" in cfg


async def test_ws_get_config_has_state(ws):
    """get_config result includes state field."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "state" in cfg


async def test_ws_get_config_state_running(ws):
    """get_config state is RUNNING."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert cfg["state"] == "RUNNING"



async def test_ws_get_config_has_location_name(ws):
    """get_config result includes location_name."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "location_name" in cfg


async def test_ws_get_config_has_elevation(ws):
    """get_config result includes elevation."""
    result = await ws.send_command("get_config")
    cfg = result["result"]
    assert "elevation" in cfg
