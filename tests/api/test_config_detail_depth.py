"""
CTS -- Configuration Endpoint Detail Tests

Tests /api/config response fields in detail: unit_system nested
fields, state field, coordinate ranges, and timezone format.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_config_latitude_range(rest):
    """Config latitude is a valid latitude value."""
    data = await rest.get_config()
    assert -90 <= data["latitude"] <= 90


async def test_config_longitude_range(rest):
    """Config longitude is a valid longitude value."""
    data = await rest.get_config()
    assert -180 <= data["longitude"] <= 180


async def test_config_state_running(rest):
    """Config state is RUNNING."""
    data = await rest.get_config()
    assert data["state"] == "RUNNING"


async def test_config_timezone_format(rest):
    """Config time_zone is a tz database string."""
    data = await rest.get_config()
    tz = data["time_zone"]
    assert "/" in tz  # e.g. "America/Denver"


async def test_config_unit_system_has_length(rest):
    """Config unit_system has length field."""
    data = await rest.get_config()
    assert "length" in data["unit_system"]


async def test_config_unit_system_has_mass(rest):
    """Config unit_system has mass field."""
    data = await rest.get_config()
    assert "mass" in data["unit_system"]


async def test_config_unit_system_has_temperature(rest):
    """Config unit_system has temperature field."""
    data = await rest.get_config()
    assert "temperature" in data["unit_system"]


async def test_config_unit_system_has_volume(rest):
    """Config unit_system has volume field."""
    data = await rest.get_config()
    assert "volume" in data["unit_system"]


async def test_config_via_ws_has_unit_system(ws):
    """WS get_config includes unit_system."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    config = resp["result"]
    assert "unit_system" in config
    assert "length" in config["unit_system"]


async def test_config_elevation_is_number(rest):
    """Config elevation is numeric."""
    data = await rest.get_config()
    assert isinstance(data["elevation"], (int, float))
    assert data["elevation"] > 0
