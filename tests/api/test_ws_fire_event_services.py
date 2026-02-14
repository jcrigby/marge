"""
CTS -- WebSocket fire_event and get_services Command Tests

Tests the WS fire_event command (custom events, event_type, event_data)
and the WS get_services command (format, domain list, service entries).
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── fire_event command ────────────────────────────────────

async def test_fire_event_returns_success(ws):
    """fire_event command returns success=True."""
    resp = await ws.send_command(
        "fire_event",
        event_type="test_custom_event",
    )
    assert resp["success"] is True


async def test_fire_event_with_event_data(ws):
    """fire_event accepts event_data payload."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "fire_event",
        event_type=f"test_event_{tag}",
        event_data={"key": "value", "number": 42},
    )
    assert resp["success"] is True


async def test_fire_event_no_event_type(ws):
    """fire_event without event_type still returns success (defaults to unknown)."""
    resp = await ws.send_command("fire_event")
    assert resp["success"] is True


async def test_fire_event_empty_event_type(ws):
    """fire_event with empty string event_type returns success."""
    resp = await ws.send_command("fire_event", event_type="")
    assert resp["success"] is True


async def test_fire_event_multiple_sequential(ws):
    """Multiple fire_event calls all return success."""
    for i in range(5):
        resp = await ws.send_command(
            "fire_event",
            event_type=f"batch_event_{i}",
        )
        assert resp["success"] is True


# ── get_services command ──────────────────────────────────

async def test_get_services_returns_success(ws):
    """get_services returns success=True with result."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    assert "result" in resp


async def test_get_services_result_is_list(ws):
    """get_services result is a list of domain entries."""
    resp = await ws.send_command("get_services")
    result = resp["result"]
    assert isinstance(result, list)
    assert len(result) > 0


async def test_get_services_domain_entry_format(ws):
    """Each domain entry has 'domain' and 'services' keys."""
    resp = await ws.send_command("get_services")
    for entry in resp["result"]:
        assert "domain" in entry, f"Missing 'domain' in entry: {entry}"
        assert "services" in entry, f"Missing 'services' in entry: {entry}"
        assert isinstance(entry["services"], dict)


async def test_get_services_has_light_domain(ws):
    """get_services includes the 'light' domain."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert "light" in domains


async def test_get_services_has_switch_domain(ws):
    """get_services includes the 'switch' domain."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert "switch" in domains


async def test_get_services_has_climate_domain(ws):
    """get_services includes the 'climate' domain."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert "climate" in domains


async def test_get_services_light_has_turn_on(ws):
    """Light domain includes turn_on service."""
    resp = await ws.send_command("get_services")
    light = next(e for e in resp["result"] if e["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_get_services_service_has_description(ws):
    """Service entries have description field."""
    resp = await ws.send_command("get_services")
    light = next(e for e in resp["result"] if e["domain"] == "light")
    turn_on = light["services"]["turn_on"]
    assert "description" in turn_on


async def test_get_services_matches_rest(ws, rest):
    """WS get_services matches REST /api/services output."""
    ws_resp = await ws.send_command("get_services")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert rest_resp.status_code == 200
    rest_services = rest_resp.json()

    ws_domains = sorted(e["domain"] for e in ws_resp["result"])
    rest_domains = sorted(e["domain"] for e in rest_services)
    assert ws_domains == rest_domains


async def test_get_services_sorted_by_domain(ws):
    """get_services result is sorted alphabetically by domain."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert domains == sorted(domains)
