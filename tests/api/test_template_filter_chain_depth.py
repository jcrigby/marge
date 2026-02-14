"""
CTS -- Template Filter Chain Depth Tests

Tests template filters via WS render_template: int, float, round,
default, iif, lower, upper, trim, replace, abs, max, min, from_json,
to_json, and chained filter combinations.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _render(ws, template: str) -> str:
    resp = await ws.send_command("render_template", template=template)
    assert resp["success"] is True
    return resp["result"]["result"]


# ── int filter ──────────────────────────────────────────

async def test_int_filter(ws):
    """int filter converts string to integer."""
    result = await _render(ws, "{{ '42' | int }}")
    assert result.strip() == "42"


async def test_int_filter_float_input(ws):
    """int filter truncates float."""
    result = await _render(ws, "{{ '3.7' | float | int }}")
    assert result.strip() == "3"


# ── float filter ────────────────────────────────────────

async def test_float_filter(ws):
    """float filter converts string to float."""
    result = await _render(ws, "{{ '3.14' | float }}")
    assert "3.14" in result


# ── round filter ────────────────────────────────────────

async def test_round_filter(ws):
    """round filter rounds to specified precision."""
    result = await _render(ws, "{{ 3.14159 | round(2) }}")
    assert "3.14" in result


async def test_round_filter_zero(ws):
    """round(0) rounds to integer."""
    result = await _render(ws, "{{ 3.7 | round(0) }}")
    assert "4" in result


# ── default filter ──────────────────────────────────────

async def test_default_filter_undefined(ws):
    """default provides fallback for undefined vars."""
    result = await _render(ws, "{{ x | default('N/A') }}")
    assert result.strip() == "N/A"


async def test_default_filter_defined(rest, ws):
    """default doesn't override defined value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.df_{tag}"
    await rest.set_state(eid, "100")
    result = await _render(ws, "{{ states('" + eid + "') | default('N/A') }}")
    assert result.strip() == "100"


# ── lower / upper filters ──────────────────────────────

async def test_lower_filter(ws):
    """lower filter converts to lowercase."""
    result = await _render(ws, "{{ 'HELLO World' | lower }}")
    assert result.strip() == "hello world"


async def test_upper_filter(ws):
    """upper filter converts to uppercase."""
    result = await _render(ws, "{{ 'hello World' | upper }}")
    assert result.strip() == "HELLO WORLD"


# ── trim filter ─────────────────────────────────────────

async def test_trim_filter(ws):
    """trim filter removes whitespace."""
    result = await _render(ws, "{{ '  hello  ' | trim }}")
    assert result.strip() == "hello"


# ── replace filter ──────────────────────────────────────

async def test_replace_filter(ws):
    """replace filter substitutes text."""
    result = await _render(ws, "{{ 'hello world' | replace('world', 'marge') }}")
    assert result.strip() == "hello marge"


# ── abs filter ──────────────────────────────────────────

async def test_abs_filter(ws):
    """abs filter returns absolute value."""
    result = await _render(ws, "{{ -42 | abs }}")
    assert float(result.strip()) == 42.0


# ── max / min filters ──────────────────────────────────

async def test_max_filter(ws):
    """max filter returns the larger value."""
    result = await _render(ws, "{{ 5 | max(10) }}")
    assert float(result.strip()) == 10.0


async def test_min_filter(ws):
    """min filter returns the smaller value."""
    result = await _render(ws, "{{ 5 | min(10) }}")
    assert float(result.strip()) == 5.0


# ── Chained filters ────────────────────────────────────

async def test_chained_float_round(ws):
    """Chained float and round filters."""
    result = await _render(ws, "{{ '3.14159' | float | round(2) }}")
    assert "3.14" in result


async def test_chained_state_int_multiply(rest, ws):
    """Chain: states() | int * 2."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.chain_{tag}"
    await rest.set_state(eid, "50")
    result = await _render(ws, "{{ states('" + eid + "') | int * 2 }}")
    assert result.strip() == "100"


# ── Global functions ────────────────────────────────────

async def test_int_function(ws):
    """int() global function."""
    result = await _render(ws, "{{ int('42') }}")
    assert result.strip() == "42"


async def test_float_function(ws):
    """float() global function."""
    result = await _render(ws, "{{ float('3.14') }}")
    assert "3.14" in result


async def test_bool_function_true(ws):
    """bool() function on truthy value."""
    result = await _render(ws, "{{ bool(1) }}")
    assert result.strip().lower() == "true"


async def test_bool_function_false(ws):
    """bool() function on falsy value."""
    result = await _render(ws, "{{ bool(0) }}")
    assert result.strip().lower() == "false"
