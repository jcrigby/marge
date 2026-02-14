"""
CTS -- Template State-Aware Functions Depth Tests

Tests the template engine's state-aware functions via WS render_template:
states(), is_state(), state_attr(), now(), and combined expressions.
Also tests template filters (int, float, round, default, lower, upper, etc.)
with state machine context.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _render(ws, template: str) -> str:
    resp = await ws.send_command("render_template", template=template)
    assert resp["success"] is True
    return resp["result"]["result"]


# ── states() function ───────────────────────────────────

async def test_states_returns_entity_state(rest, ws):
    """states('entity_id') returns the entity's state string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_st_{tag}"
    await rest.set_state(eid, "42")
    result = await _render(ws, "{{ states('" + eid + "') }}")
    assert result.strip() == "42"


async def test_states_unknown_entity(ws):
    """states() returns 'unknown' for non-existent entity."""
    result = await _render(ws, "{{ states('sensor.nonexistent_xyz_99') }}")
    assert result.strip() == "unknown"


# ── is_state() function ────────────────────────────────

async def test_is_state_true(rest, ws):
    """is_state() returns true when entity matches expected state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_is_{tag}"
    await rest.set_state(eid, "on")
    result = await _render(ws, "{{ is_state('" + eid + "', 'on') }}")
    assert result.strip().lower() == "true"


async def test_is_state_false(rest, ws):
    """is_state() returns false when entity doesn't match."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_isf_{tag}"
    await rest.set_state(eid, "off")
    result = await _render(ws, "{{ is_state('" + eid + "', 'on') }}")
    assert result.strip().lower() == "false"


async def test_is_state_nonexistent(ws):
    """is_state() returns false for non-existent entity."""
    result = await _render(ws, "{{ is_state('sensor.nope_xyz_99', 'on') }}")
    assert result.strip().lower() == "false"


# ── state_attr() function ──────────────────────────────

async def test_state_attr_returns_value(rest, ws):
    """state_attr() returns the attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_sa_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    result = await _render(ws, "{{ state_attr('" + eid + "', 'unit') }}")
    assert result.strip() == "W"


async def test_state_attr_friendly_name(rest, ws):
    """state_attr() can read friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_fn_{tag}"
    await rest.set_state(eid, "55", {"friendly_name": f"Power {tag}"})
    result = await _render(ws, "{{ state_attr('" + eid + "', 'friendly_name') }}")
    assert tag in result


# ── now() function ──────────────────────────────────────

async def test_now_returns_timestamp(ws):
    """now() returns a timestamp-like string."""
    result = await _render(ws, "{{ now() }}")
    # Should contain date-like pattern: YYYY-MM-DD
    assert "20" in result  # year prefix
    assert "-" in result   # date separator
    assert "T" in result   # time separator


# ── Combined Expressions ────────────────────────────────

async def test_template_conditional(rest, ws):
    """Template conditional based on entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_cond_{tag}"
    await rest.set_state(eid, "on")
    template = "{% if is_state('" + eid + "', 'on') %}yes{% else %}no{% endif %}"
    result = await _render(ws, template)
    assert result.strip() == "yes"


async def test_template_arithmetic(rest, ws):
    """Template with arithmetic on state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_math_{tag}"
    await rest.set_state(eid, "100")
    template = "{{ states('" + eid + "') | int * 2 }}"
    result = await _render(ws, template)
    assert result.strip() == "200"


async def test_template_float_filter(rest, ws):
    """Template float filter converts state to float."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_flt_{tag}"
    await rest.set_state(eid, "3.14")
    template = "{{ states('" + eid + "') | float | round(1) }}"
    result = await _render(ws, template)
    assert "3.1" in result


async def test_template_default_filter(ws):
    """default filter provides fallback for undefined values."""
    result = await _render(ws, "{{ undefined_var | default('fallback') }}")
    assert result.strip() == "fallback"


async def test_template_lower_upper(ws):
    """lower and upper filters work."""
    result = await _render(ws, "{{ 'Hello' | lower }}")
    assert result.strip() == "hello"
    result = await _render(ws, "{{ 'Hello' | upper }}")
    assert result.strip() == "HELLO"
