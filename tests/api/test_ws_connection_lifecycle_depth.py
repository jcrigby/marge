"""
CTS -- WS Connection Lifecycle Depth Tests

Tests WebSocket connection lifecycle: auth flow, ping/pong, multiple
subscriptions, unsubscribe_events, and multiple concurrent connections.
"""

import asyncio
import json
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Auth Flow ─────────────────────────────────────────────

async def test_ws_ping_returns_pong(ws):
    """WS ping returns pong response."""
    result = await ws.ping()
    assert result is True


async def test_ws_ping_multiple_times(ws):
    """Multiple WS pings all return pong."""
    for _ in range(5):
        result = await ws.ping()
        assert result is True


# ── Subscribe/Unsubscribe Events ─────────────────────────

async def test_ws_subscribe_events(ws):
    """WS subscribe_events succeeds."""
    result = await ws.subscribe_events()
    assert result is not None


async def test_ws_receive_event_after_subscribe(rest, ws):
    """WS receives events after subscribe_events."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_ev_{tag}"
    await ws.subscribe_events()
    await rest.set_state(eid, "42")
    event = await ws.recv_event(timeout=3.0)
    assert event["event"]["data"]["entity_id"] == eid


async def test_ws_unsubscribe_events(ws):
    """WS unsubscribe_events succeeds."""
    sub = await ws.subscribe_events()
    result = await ws.send_command("unsubscribe_events", subscription=sub)
    assert result.get("success") is True


# ── Get Config ────────────────────────────────────────────

async def test_ws_get_config(ws):
    """WS get_config returns system configuration."""
    result = await ws.send_command("get_config")
    assert result.get("success") is True
    config = result.get("result", {})
    assert "location_name" in config
    assert "version" in config
    assert config["location_name"] == "Marge Demo Home"


async def test_ws_get_config_has_coordinates(ws):
    """WS config has latitude and longitude."""
    result = await ws.send_command("get_config")
    config = result.get("result", {})
    assert "latitude" in config
    assert "longitude" in config
    assert isinstance(config["latitude"], (int, float))


async def test_ws_get_config_has_timezone(ws):
    """WS config has time_zone."""
    result = await ws.send_command("get_config")
    config = result.get("result", {})
    assert "time_zone" in config
    assert config["time_zone"] == "America/Denver"


# ── Get Services ──────────────────────────────────────────

async def test_ws_get_services(ws):
    """WS get_services returns service registry."""
    result = await ws.send_command("get_services")
    assert result.get("success") is True
    services = result.get("result", [])
    assert isinstance(services, list)
    assert len(services) > 0


async def test_ws_get_services_has_domains(ws):
    """WS services list includes known domains."""
    result = await ws.send_command("get_services")
    services = result.get("result", [])
    domains = [s.get("domain") for s in services]
    assert "light" in domains
    assert "switch" in domains


# ── Fire Event ────────────────────────────────────────────

async def test_ws_fire_event(ws):
    """WS fire_event succeeds."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "fire_event",
        event_type=f"test_event_{tag}",
    )
    assert result.get("success") is True
