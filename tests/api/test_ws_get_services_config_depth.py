"""
CTS -- WS get_services and get_config Detail Depth Tests

Tests WebSocket get_services returns domain-grouped service listings
with expected domains and services. Tests get_config returns location,
coordinates, units, timezone, version, and state.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── get_services ────────────────────────────────────────

async def test_get_services_returns_list(ws):
    """WS get_services returns a list of domain objects."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    services = resp["result"]
    assert isinstance(services, list)
    assert len(services) > 0


async def test_get_services_has_light_domain(ws):
    """get_services includes light domain."""
    resp = await ws.send_command("get_services")
    domains = [s["domain"] for s in resp["result"]]
    assert "light" in domains


async def test_get_services_has_switch_domain(ws):
    """get_services includes switch domain."""
    resp = await ws.send_command("get_services")
    domains = [s["domain"] for s in resp["result"]]
    assert "switch" in domains


async def test_get_services_light_has_turn_on(ws):
    """light domain has turn_on service."""
    resp = await ws.send_command("get_services")
    light = next(s for s in resp["result"] if s["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_get_services_light_has_turn_off(ws):
    """light domain has turn_off service."""
    resp = await ws.send_command("get_services")
    light = next(s for s in resp["result"] if s["domain"] == "light")
    assert "turn_off" in light["services"]


async def test_get_services_has_climate(ws):
    """get_services includes climate domain."""
    resp = await ws.send_command("get_services")
    domains = [s["domain"] for s in resp["result"]]
    assert "climate" in domains


async def test_get_services_has_lock(ws):
    """get_services includes lock domain."""
    resp = await ws.send_command("get_services")
    domains = [s["domain"] for s in resp["result"]]
    assert "lock" in domains


async def test_get_services_domain_has_services(ws):
    """Each domain entry has a services object."""
    resp = await ws.send_command("get_services")
    for entry in resp["result"]:
        assert "domain" in entry
        assert "services" in entry
        assert isinstance(entry["services"], dict)


# ── get_config ──────────────────────────────────────────

async def test_get_config_has_location_name(ws):
    """WS get_config returns location_name."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    config = resp["result"]
    assert config["location_name"] == "Marge Demo Home"


async def test_get_config_has_coordinates(ws):
    """WS get_config returns latitude and longitude."""
    resp = await ws.send_command("get_config")
    config = resp["result"]
    assert abs(config["latitude"] - 40.3916) < 0.01
    assert abs(config["longitude"] - (-111.8508)) < 0.01


async def test_get_config_has_timezone(ws):
    """WS get_config returns time_zone."""
    resp = await ws.send_command("get_config")
    config = resp["result"]
    assert config["time_zone"] == "America/Denver"


async def test_get_config_has_unit_system(ws):
    """WS get_config returns unit_system with expected values."""
    resp = await ws.send_command("get_config")
    units = resp["result"]["unit_system"]
    assert units["length"] == "mi"
    assert units["mass"] == "lb"
    assert units["volume"] == "gal"


async def test_get_config_has_version(ws):
    """WS get_config returns version string."""
    resp = await ws.send_command("get_config")
    config = resp["result"]
    assert "version" in config
    assert isinstance(config["version"], str)


async def test_get_config_state_running(ws):
    """WS get_config state is RUNNING."""
    resp = await ws.send_command("get_config")
    config = resp["result"]
    assert config["state"] == "RUNNING"


async def test_get_config_has_elevation(ws):
    """WS get_config returns elevation."""
    resp = await ws.send_command("get_config")
    config = resp["result"]
    assert config["elevation"] == 1387
