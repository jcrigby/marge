"""
CTS -- WebSocket Ping, Command Ordering, and Edge Case Tests

Tests WS ping/pong, multiple sequential commands, unknown command
handling, subscribe/unsubscribe, template rendering, and call_service.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_ping_pong(ws):
    """WS ping returns pong."""
    result = await ws.ping()
    assert result is True


async def test_ws_multiple_pings(ws):
    """Multiple pings all return pong."""
    for _ in range(5):
        result = await ws.ping()
        assert result is True


async def test_ws_sequential_commands(ws):
    """Multiple sequential WS commands all succeed."""
    # Ping
    assert await ws.ping() is True

    # Get config
    r1 = await ws.send_command("get_config")
    assert r1.get("success", False) is True

    # Render template
    r2 = await ws.send_command("render_template", template="{{ 1 + 1 }}")
    assert r2.get("success", False) is True

    # Get services
    r3 = await ws.send_command("get_services")
    assert r3.get("success", False) is True


async def test_ws_subscribe_unsubscribe(ws):
    """Subscribe then unsubscribe completes without error."""
    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    assert sub.get("success", False) is True
    sub_id = sub["id"]

    unsub = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert unsub.get("success", False) is True


async def test_ws_call_service_light(ws, rest):
    """WS call_service for light works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsord_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_get_config_has_fields(ws):
    """WS get_config returns expected config fields."""
    resp = await ws.send_command("get_config")
    assert resp.get("success", False) is True
    result = resp.get("result", {})
    assert "version" in result
    assert "location_name" in result


async def test_ws_get_services_returns_list(ws):
    """WS get_services returns a list of domain/service entries."""
    resp = await ws.send_command("get_services")
    assert resp.get("success", False) is True
    result = resp.get("result", [])
    assert isinstance(result, list)
    assert len(result) > 0
    # Each entry should have domain and services keys
    domains = [e["domain"] for e in result]
    assert "light" in domains
    assert "switch" in domains
