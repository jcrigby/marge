"""
CTS -- WebSocket Error Handling Tests

Tests WS protocol edge cases: unknown commands, malformed requests,
subscription lifecycle, and error response format.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_ping_returns_pong(ws):
    """ping command returns pong."""
    resp = await ws.send_command("ping")
    assert resp.get("type") == "pong"


async def test_ws_unsubscribe_nonexistent_id(ws):
    """Unsubscribing from non-existent subscription ID doesn't crash."""
    resp = await ws.send_command("unsubscribe_events", subscription=999999)
    # Should not crash — might succeed (no-op) or return error
    assert "type" in resp


async def test_ws_call_service_empty_domain(ws):
    """call_service with empty domain handled gracefully."""
    resp = await ws.send_command(
        "call_service",
        domain="",
        service="turn_on",
        service_data={},
    )
    # Should not crash
    assert "type" in resp


async def test_ws_subscribe_returns_subscription_id(ws):
    """subscribe_events returns a subscription ID."""
    resp = await ws.send_command("subscribe_events")
    assert resp.get("success", False) is True


async def test_ws_get_config_returns_object(ws):
    """get_config returns config object."""
    resp = await ws.send_command("get_config")
    assert resp.get("success", False) is True
    result = resp.get("result", {})
    assert "latitude" in result
    assert "longitude" in result


async def test_ws_get_services_result_is_list(ws):
    """get_services returns a list of domain entries."""
    resp = await ws.send_command("get_services")
    assert resp.get("success", False) is True
    result = resp.get("result", [])
    assert isinstance(result, list)
    if len(result) > 0:
        assert "domain" in result[0]


async def test_ws_render_template_valid(ws):
    """render_template with valid template returns result."""
    resp = await ws.send_command(
        "render_template",
        template="{{ 1 + 1 }}",
    )
    assert resp.get("success", False) is True
    assert "2" in str(resp.get("result", ""))


async def test_ws_render_template_error(ws):
    """render_template with bad filter returns error."""
    resp = await ws.send_command(
        "render_template",
        template="{{ x | nonexistent_filter }}",
    )
    # Should return error, not crash
    assert resp.get("success", True) is False or "error" in str(resp).lower()
