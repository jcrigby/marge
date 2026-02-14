"""
CTS -- WS Advanced Commands Depth Tests

Tests WebSocket command semantics: ping/pong, fire_event,
render_template edge cases, get_services, get_notifications,
subscribe_trigger, lovelace/config, and unknown command handling.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Ping / Pong ──────────────────────────────────────────

async def test_ws_ping_returns_pong(ws):
    """WS ping returns pong response."""
    result = await ws.send_command("ping")
    # ping returns type: pong (not the usual result envelope)
    assert result.get("type") == "pong" or result.get("success") is True


async def test_ws_ping_echoes_id(ws):
    """WS ping response echoes the request id."""
    result = await ws.send_command("ping")
    # Response should include the id
    assert "id" in result


async def test_ws_ping_multiple_sequential(ws):
    """Multiple sequential pings all succeed."""
    for _ in range(5):
        result = await ws.send_command("ping")
        assert result.get("type") == "pong" or result.get("success") is True


# ── Fire Event ───────────────────────────────────────────

async def test_ws_fire_event_success(ws):
    """WS fire_event returns success."""
    result = await ws.send_command(
        "fire_event",
        event_type="test_event",
    )
    assert result["success"] is True


async def test_ws_fire_event_custom_type(ws):
    """WS fire_event with custom event type succeeds."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "fire_event",
        event_type=f"custom.my_event_{tag}",
    )
    assert result["success"] is True


# ── Render Template ──────────────────────────────────────

async def test_ws_render_template_literal(ws):
    """WS render_template with literal text returns it."""
    result = await ws.send_command(
        "render_template",
        template="hello world",
    )
    assert result["success"] is True
    assert result["result"]["result"] == "hello world"


async def test_ws_render_template_states_function(rest, ws):
    """WS render_template with states() function reads entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ws_tpl_{tag}"
    await rest.set_state(eid, "42")

    result = await ws.send_command(
        "render_template",
        template=f"{{{{ states('{eid}') }}}}",
    )
    assert result["success"] is True
    assert result["result"]["result"] == "42"


async def test_ws_render_template_now_function(ws):
    """WS render_template with now() returns a timestamp."""
    result = await ws.send_command(
        "render_template",
        template="{{ now() }}",
    )
    assert result["success"] is True
    rendered = result["result"]["result"]
    # Should contain date-like content (year at minimum)
    assert "20" in rendered


async def test_ws_render_template_math(ws):
    """WS render_template with arithmetic works."""
    result = await ws.send_command(
        "render_template",
        template="{{ 2 + 3 }}",
    )
    assert result["success"] is True
    assert result["result"]["result"].strip() == "5"


# ── Get Services ─────────────────────────────────────────

async def test_ws_get_services_success(ws):
    """WS get_services returns success."""
    result = await ws.send_command("get_services")
    assert result["success"] is True


async def test_ws_get_services_has_domains(ws):
    """WS get_services result contains known domains."""
    result = await ws.send_command("get_services")
    svc = result["result"]
    domains = [s["domain"] for s in svc]
    assert "light" in domains
    assert "switch" in domains


# ── Get Notifications ────────────────────────────────────

async def test_ws_get_notifications_returns_array(ws):
    """WS get_notifications returns a list."""
    result = await ws.send_command("get_notifications")
    assert result["success"] is True
    assert isinstance(result["result"], list)


# ── Subscribe Trigger ────────────────────────────────────

async def test_ws_subscribe_trigger_success(ws):
    """WS subscribe_trigger returns success."""
    result = await ws.send_command("subscribe_trigger")
    assert result["success"] is True


# ── Lovelace Config ──────────────────────────────────────

async def test_ws_lovelace_config_has_views(ws):
    """WS lovelace/config returns views array."""
    result = await ws.send_command("lovelace/config")
    assert result["success"] is True
    assert "views" in result["result"]
    assert isinstance(result["result"]["views"], list)


async def test_ws_lovelace_config_has_title(ws):
    """WS lovelace/config returns title."""
    result = await ws.send_command("lovelace/config")
    assert result["result"]["title"] == "Marge"


# ── Unknown Command ──────────────────────────────────────

async def test_ws_unknown_command_fails(ws):
    """WS unknown command returns success=false."""
    result = await ws.send_command("nonexistent_command_xyz")
    assert result["success"] is False
