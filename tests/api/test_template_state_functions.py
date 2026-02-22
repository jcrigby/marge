"""
CTS -- Template State Function Tests

Tests template rendering with state-aware functions:
states(), is_state(), state_attr(), and now().
Requires entities to be pre-set for the template context.
Covers both REST /api/template and WS render_template.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _render_rest(rest, template):
    """POST /api/template and return response."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    return resp


async def _render_ws(ws, template: str) -> str:
    """Render template via WS render_template command."""
    return await ws.render_template(template)


# ── states() function ───────────────────────────────────

async def test_states_function_returns_value(rest):
    """states('entity_id') returns current state value."""
    await rest.set_state("sensor.tpl_states", "72.5")
    resp = await _render_rest(rest, "{{ states('sensor.tpl_states') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "72.5"


async def test_states_unknown_entity(rest):
    """states() returns 'unknown' for nonexistent entity."""
    resp = await _render_rest(rest, "{{ states('sensor.does_not_exist_xyz') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "unknown"


# ── is_state() function ────────────────────────────────

async def test_is_state_true(rest):
    """is_state() returns true when state matches."""
    await rest.set_state("light.tpl_is_state", "on")
    resp = await _render_rest(rest, "{{ is_state('light.tpl_is_state', 'on') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_is_state_false(rest):
    """is_state() returns false when state doesn't match."""
    await rest.set_state("light.tpl_is_state2", "off")
    resp = await _render_rest(rest, "{{ is_state('light.tpl_is_state2', 'on') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_is_state_nonexistent(rest):
    """is_state() returns false for nonexistent entity."""
    resp = await _render_rest(rest, "{{ is_state('sensor.nonexistent_xyz', 'on') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


# ── state_attr() function ──────────────────────────────

async def test_state_attr_returns_value(rest):
    """state_attr() returns attribute value."""
    await rest.set_state("sensor.tpl_attr", "ok", {"unit": "celsius", "precision": 2})
    resp = await _render_rest(rest, "{{ state_attr('sensor.tpl_attr', 'unit') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "celsius"


async def test_state_attr_numeric(rest):
    """state_attr() returns numeric attribute value."""
    await rest.set_state("sensor.tpl_attr_num", "ok", {"count": 42})
    resp = await _render_rest(rest, "{{ state_attr('sensor.tpl_attr_num', 'count') }}")
    assert resp.status_code == 200
    assert "42" in resp.text.strip()


async def test_state_attr_missing_attr(rest):
    """state_attr() for missing attribute returns none/empty."""
    await rest.set_state("sensor.tpl_attr_miss", "ok")
    resp = await _render_rest(rest, "{{ state_attr('sensor.tpl_attr_miss', 'nonexistent') }}")
    assert resp.status_code == 200
    # Should return none, empty string, or "None"
    result = resp.text.strip().lower()
    assert result in ["", "none", "null", "undefined"]


# ── now() function ──────────────────────────────────────

async def test_now_function(rest):
    """now() returns current timestamp."""
    resp = await _render_rest(rest, "{{ now() }}")
    assert resp.status_code == 200
    assert "20" in resp.text  # Year 20xx


# ── Combined Expressions ────────────────────────────────

async def test_states_in_conditional(rest):
    """states() used in conditional template."""
    await rest.set_state("sensor.tpl_cond", "on")
    resp = await _render_rest(rest, "{% if states('sensor.tpl_cond') == 'on' %}yes{% else %}no{% endif %}")
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


async def test_states_with_math(rest):
    """states() result used in arithmetic."""
    await rest.set_state("sensor.tpl_math", "25")
    resp = await _render_rest(rest, "{{ states('sensor.tpl_math') | float + 10 }}")
    assert resp.status_code == 200
    assert "35" in resp.text.strip()


async def test_multiple_state_functions(rest):
    """Multiple state functions in one template."""
    await rest.set_state("sensor.tpl_multi_a", "hot")
    await rest.set_state("sensor.tpl_multi_b", "cold")
    resp = await _render_rest(rest, "{{ states('sensor.tpl_multi_a') }} and {{ states('sensor.tpl_multi_b') }}")
    assert resp.status_code == 200
    assert "hot" in resp.text
    assert "cold" in resp.text


async def test_is_state_in_template_logic(rest):
    """is_state() in template if/else logic."""
    await rest.set_state("light.tpl_logic", "off")
    resp = await _render_rest(rest, "{% if is_state('light.tpl_logic', 'on') %}bright{% else %}dark{% endif %}")
    assert resp.status_code == 200
    assert resp.text.strip() == "dark"


# ── Merged from depth: WS-based state function tests ────

@pytest.mark.marge_only
async def test_ws_states_returns_entity_state(rest, ws):
    """states('entity_id') returns the entity's state string via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_st_{tag}"
    await rest.set_state(eid, "42")
    result = await _render_ws(ws, "{{ states('" + eid + "') }}")
    assert result.strip() == "42"


@pytest.mark.marge_only
async def test_ws_states_unknown_entity(ws):
    """states() returns 'unknown' for non-existent entity via WS."""
    result = await _render_ws(ws, "{{ states('sensor.nonexistent_xyz_99') }}")
    assert result.strip() == "unknown"


@pytest.mark.marge_only
async def test_ws_is_state_true(rest, ws):
    """is_state() returns true when entity matches expected state via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_is_{tag}"
    await rest.set_state(eid, "on")
    result = await _render_ws(ws, "{{ is_state('" + eid + "', 'on') }}")
    assert result.strip().lower() == "true"


@pytest.mark.marge_only
async def test_ws_is_state_false(rest, ws):
    """is_state() returns false when entity doesn't match via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_isf_{tag}"
    await rest.set_state(eid, "off")
    result = await _render_ws(ws, "{{ is_state('" + eid + "', 'on') }}")
    assert result.strip().lower() == "false"


@pytest.mark.marge_only
async def test_ws_is_state_nonexistent(ws):
    """is_state() returns false for non-existent entity via WS."""
    result = await _render_ws(ws, "{{ is_state('sensor.nope_xyz_99', 'on') }}")
    assert result.strip().lower() == "false"


@pytest.mark.marge_only
async def test_ws_state_attr_returns_value(rest, ws):
    """state_attr() returns the attribute value via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_sa_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    result = await _render_ws(ws, "{{ state_attr('" + eid + "', 'unit') }}")
    assert result.strip() == "W"


@pytest.mark.marge_only
async def test_ws_state_attr_friendly_name(rest, ws):
    """state_attr() can read friendly_name via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_fn_{tag}"
    await rest.set_state(eid, "55", {"friendly_name": f"Power {tag}"})
    result = await _render_ws(ws, "{{ state_attr('" + eid + "', 'friendly_name') }}")
    assert tag in result


@pytest.mark.marge_only
async def test_ws_now_returns_timestamp(ws):
    """now() returns a timestamp-like string via WS."""
    result = await _render_ws(ws, "{{ now() }}")
    # Should contain date-like pattern: YYYY-MM-DD
    assert "20" in result  # year prefix
    assert "-" in result   # date separator
    assert "T" in result   # time separator


@pytest.mark.marge_only
async def test_ws_template_conditional(rest, ws):
    """Template conditional based on entity state via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tmpl_cond_{tag}"
    await rest.set_state(eid, "on")
    template = "{% if is_state('" + eid + "', 'on') %}yes{% else %}no{% endif %}"
    result = await _render_ws(ws, template)
    assert result.strip() == "yes"


@pytest.mark.marge_only
async def test_ws_template_arithmetic(rest, ws):
    """Template with arithmetic on state value via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_math_{tag}"
    await rest.set_state(eid, "100")
    template = "{{ states('" + eid + "') | int * 2 }}"
    result = await _render_ws(ws, template)
    assert result.strip() == "200"


@pytest.mark.marge_only
async def test_ws_template_float_filter(rest, ws):
    """Template float filter converts state to float via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_flt_{tag}"
    await rest.set_state(eid, "3.14")
    template = "{{ states('" + eid + "') | float | round(1) }}"
    result = await _render_ws(ws, template)
    assert "3.1" in result


@pytest.mark.marge_only
async def test_ws_template_default_filter(ws):
    """default filter provides fallback for undefined values via WS."""
    result = await _render_ws(ws, "{{ undefined_var | default('fallback') }}")
    assert result.strip() == "fallback"


@pytest.mark.marge_only
async def test_ws_template_lower_upper(ws):
    """lower and upper filters work via WS."""
    result = await _render_ws(ws, "{{ 'Hello' | lower }}")
    assert result.strip() == "hello"
    result = await _render_ws(ws, "{{ 'Hello' | upper }}")
    assert result.strip() == "HELLO"
