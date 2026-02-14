"""
CTS -- WebSocket Template Rendering Tests

Tests the render_template WebSocket command with various template
expressions, state-aware functions, and streaming responses.
"""

import asyncio
import json
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_render_simple_template(ws):
    """WS render_template with simple expression."""
    resp = await ws.send_command(
        "render_template",
        template="{{ 1 + 2 }}",
    )
    assert resp["success"] is True
    assert "result" in resp


async def test_ws_render_string_template(ws):
    """WS render_template with string expression."""
    resp = await ws.send_command(
        "render_template",
        template="{{ 'hello world' | upper }}",
    )
    assert resp["success"] is True
    result = resp["result"]
    # Result could be in "result" key or nested
    if isinstance(result, dict) and "result" in result:
        assert result["result"].strip() == "HELLO WORLD"
    elif isinstance(result, str):
        assert result.strip() == "HELLO WORLD"


async def test_ws_render_math_template(ws):
    """WS render_template with math."""
    resp = await ws.send_command(
        "render_template",
        template="{{ (10 * 5) - 8 }}",
    )
    assert resp["success"] is True


async def test_ws_render_state_template(ws, rest):
    """WS render_template accessing entity state."""
    await rest.set_state("sensor.ws_tmpl_test", "42")
    resp = await ws.send_command(
        "render_template",
        template="{{ states('sensor.ws_tmpl_test') }}",
    )
    assert resp["success"] is True


async def test_ws_render_is_state_template(ws, rest):
    """WS render_template with is_state function."""
    await rest.set_state("sensor.ws_tmpl_is", "on")
    resp = await ws.send_command(
        "render_template",
        template="{{ is_state('sensor.ws_tmpl_is', 'on') }}",
    )
    assert resp["success"] is True


async def test_ws_render_state_attr_template(ws, rest):
    """WS render_template with state_attr function."""
    await rest.set_state("sensor.ws_tmpl_attr", "50", {"unit": "percent"})
    resp = await ws.send_command(
        "render_template",
        template="{{ state_attr('sensor.ws_tmpl_attr', 'unit') }}",
    )
    assert resp["success"] is True


async def test_ws_render_filter_chain(ws):
    """WS render_template with filter chain."""
    resp = await ws.send_command(
        "render_template",
        template="{{ '  3.14159  ' | trim | float | round(2) }}",
    )
    assert resp["success"] is True


async def test_ws_render_conditional(ws):
    """WS render_template with conditional expression."""
    resp = await ws.send_command(
        "render_template",
        template="{{ 'yes' if 1 == 1 else 'no' }}",
    )
    assert resp["success"] is True


async def test_ws_render_now_function(ws):
    """WS render_template with now() function."""
    resp = await ws.send_command(
        "render_template",
        template="{{ now() }}",
    )
    assert resp["success"] is True


async def test_ws_render_iif_filter(ws):
    """WS render_template with iif filter."""
    resp = await ws.send_command(
        "render_template",
        template="{{ true | iif('on', 'off') }}",
    )
    assert resp["success"] is True
