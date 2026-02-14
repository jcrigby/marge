"""
CTS -- WS Render Template Edge Cases Depth Tests

Tests WS render_template with edge cases: empty template, boolean
expressions, conditional logic, filter chains, undefined variables,
and complex expressions.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Expressions ────────────────────────────────────

async def test_ws_template_empty_string(ws):
    """WS render_template with empty string returns empty."""
    result = await ws.send_command("render_template", template="")
    assert result["success"] is True
    assert result["result"]["result"] == ""


async def test_ws_template_boolean_true(ws):
    """WS render_template with boolean true."""
    result = await ws.send_command("render_template", template="{{ true }}")
    assert result["success"] is True
    assert result["result"]["result"].strip().lower() == "true"


async def test_ws_template_boolean_false(ws):
    """WS render_template with boolean false."""
    result = await ws.send_command("render_template", template="{{ false }}")
    assert result["success"] is True
    assert result["result"]["result"].strip().lower() == "false"


async def test_ws_template_comparison(ws):
    """WS render_template with comparison."""
    result = await ws.send_command("render_template", template="{{ 5 > 3 }}")
    assert result["success"] is True
    assert result["result"]["result"].strip().lower() == "true"


async def test_ws_template_if_else(ws):
    """WS render_template with if/else."""
    result = await ws.send_command(
        "render_template",
        template="{% if 1 == 1 %}yes{% else %}no{% endif %}",
    )
    assert result["success"] is True
    assert result["result"]["result"] == "yes"


# ── Filter Chains ────────────────────────────────────────

async def test_ws_template_int_filter(ws):
    """WS render_template with int filter."""
    result = await ws.send_command("render_template", template="{{ '42' | int }}")
    assert result["success"] is True
    assert result["result"]["result"].strip() == "42"


async def test_ws_template_float_round(ws):
    """WS render_template with float and round."""
    result = await ws.send_command(
        "render_template",
        template="{{ 3.14159 | round(2) }}",
    )
    assert result["success"] is True
    assert "3.14" in result["result"]["result"]


async def test_ws_template_lower_upper(ws):
    """WS render_template with lower/upper filters."""
    result = await ws.send_command("render_template", template="{{ 'Hello' | lower }}")
    assert result["result"]["result"].strip() == "hello"

    result2 = await ws.send_command("render_template", template="{{ 'hello' | upper }}")
    assert result2["result"]["result"].strip() == "HELLO"


# ── State-Aware Functions ────────────────────────────────

async def test_ws_template_states_nonexistent(rest, ws):
    """WS render_template states() for nonexistent entity returns 'unknown'."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "render_template",
        template=f"{{{{ states('sensor.nope_{tag}') }}}}",
    )
    assert result["success"] is True
    # Should return "unknown" or empty for nonexistent entities
    rendered = result["result"]["result"].strip()
    assert rendered in ("unknown", "", "None")


async def test_ws_template_is_state_nonexistent(ws):
    """WS render_template is_state() for nonexistent entity returns false."""
    tag = uuid.uuid4().hex[:8]
    result = await ws.send_command(
        "render_template",
        template=f"{{{{ is_state('sensor.nope_{tag}', 'on') }}}}",
    )
    assert result["success"] is True
    assert result["result"]["result"].strip().lower() == "false"


# ── Complex Expressions ──────────────────────────────────

async def test_ws_template_for_loop(ws):
    """WS render_template with for loop."""
    result = await ws.send_command(
        "render_template",
        template="{% for i in range(3) %}{{ i }}{% endfor %}",
    )
    assert result["success"] is True
    assert result["result"]["result"] == "012"


async def test_ws_template_multiplication(ws):
    """WS render_template with multiplication."""
    result = await ws.send_command("render_template", template="{{ 6 * 7 }}")
    assert result["success"] is True
    assert result["result"]["result"].strip() == "42"
