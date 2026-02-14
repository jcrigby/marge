"""
CTS -- WS Service Listing Structure Depth Tests

Tests WebSocket get_services response: array format, domain
entries, service keys, and known domain presence.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Get Services Response ───────────────────────────────

async def test_ws_get_services_success(ws):
    """get_services returns success."""
    result = await ws.send_command("get_services")
    assert result["success"] is True


async def test_ws_get_services_is_array(ws):
    """get_services result is an array."""
    result = await ws.send_command("get_services")
    assert isinstance(result["result"], list)


async def test_ws_get_services_entry_has_domain(ws):
    """Each service entry has domain field."""
    result = await ws.send_command("get_services")
    for entry in result["result"]:
        assert "domain" in entry


async def test_ws_get_services_entry_has_services(ws):
    """Each service entry has services field."""
    result = await ws.send_command("get_services")
    for entry in result["result"]:
        assert "services" in entry


# ── Known Domains ───────────────────────────────────────

async def test_ws_services_has_light(ws):
    """Services include light domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "light" in domains


async def test_ws_services_has_switch(ws):
    """Services include switch domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "switch" in domains


async def test_ws_services_has_climate(ws):
    """Services include climate domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "climate" in domains


async def test_ws_services_has_cover(ws):
    """Services include cover domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "cover" in domains


async def test_ws_services_has_fan(ws):
    """Services include fan domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "fan" in domains


# ── Service Details ─────────────────────────────────────

async def test_ws_services_light_has_turn_on(ws):
    """light domain has turn_on service."""
    result = await ws.send_command("get_services")
    light = next(e for e in result["result"] if e["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_ws_services_light_has_turn_off(ws):
    """light domain has turn_off service."""
    result = await ws.send_command("get_services")
    light = next(e for e in result["result"] if e["domain"] == "light")
    assert "turn_off" in light["services"]


async def test_ws_services_climate_has_set_temperature(ws):
    """climate domain has set_temperature service."""
    result = await ws.send_command("get_services")
    climate = next(e for e in result["result"] if e["domain"] == "climate")
    assert "set_temperature" in climate["services"]
