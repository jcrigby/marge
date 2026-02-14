"""
CTS -- WS Config Detail Parity Depth Tests

Tests WS get_config response fields, WS get_services detail structure,
WS subscribe/unsubscribe lifecycle, and WS fire_event response.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── WS get_config Fields ────────────────────────────────

async def test_ws_config_has_location_name(ws):
    """WS get_config result has location_name."""
    result = await ws.send_command("get_config")
    assert "location_name" in result["result"]


async def test_ws_config_has_latitude(ws):
    """WS get_config result has latitude."""
    result = await ws.send_command("get_config")
    assert "latitude" in result["result"]


async def test_ws_config_has_longitude(ws):
    """WS get_config result has longitude."""
    result = await ws.send_command("get_config")
    assert "longitude" in result["result"]


async def test_ws_config_has_elevation(ws):
    """WS get_config result has elevation."""
    result = await ws.send_command("get_config")
    assert "elevation" in result["result"]


async def test_ws_config_has_unit_system(ws):
    """WS get_config result has unit_system."""
    result = await ws.send_command("get_config")
    assert "unit_system" in result["result"]
    units = result["result"]["unit_system"]
    assert "temperature" in units
    assert "length" in units


async def test_ws_config_has_time_zone(ws):
    """WS get_config result has time_zone."""
    result = await ws.send_command("get_config")
    assert "time_zone" in result["result"]


async def test_ws_config_has_version(ws):
    """WS get_config result has version."""
    result = await ws.send_command("get_config")
    assert "version" in result["result"]


async def test_ws_config_has_state(ws):
    """WS get_config result has state field."""
    result = await ws.send_command("get_config")
    assert result["result"]["state"] == "RUNNING"


# ── WS get_services Detail ──────────────────────────────

async def test_ws_services_entry_structure(ws):
    """WS get_services entries have domain and services dict."""
    result = await ws.send_command("get_services")
    for entry in result["result"]:
        assert "domain" in entry
        assert "services" in entry
        assert isinstance(entry["services"], dict)


async def test_ws_services_has_many_domains(ws):
    """WS get_services lists at least 10 domains."""
    result = await ws.send_command("get_services")
    assert len(result["result"]) >= 10


async def test_ws_services_has_lock_domain(ws):
    """WS get_services includes lock domain."""
    result = await ws.send_command("get_services")
    domains = [e["domain"] for e in result["result"]]
    assert "lock" in domains


async def test_ws_services_lock_has_lock_service(ws):
    """Lock domain has lock service in WS listing."""
    result = await ws.send_command("get_services")
    lock = next(e for e in result["result"] if e["domain"] == "lock")
    assert "lock" in lock["services"]
    assert "unlock" in lock["services"]


# ── WS Subscribe/Unsubscribe ────────────────────────────

async def test_ws_subscribe_events_success(ws):
    """WS subscribe_events returns success."""
    result = await ws.send_command("subscribe_events")
    assert result["success"] is True


async def test_ws_unsubscribe_events_success(ws):
    """WS unsubscribe_events returns success."""
    sub = await ws.send_command("subscribe_events")
    sub_id = sub["id"]
    result = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert result["success"] is True
