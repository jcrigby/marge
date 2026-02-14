"""
CTS -- Template Rendering Depth Tests

Tests the Jinja2 template engine via POST /api/template,
including state-aware functions, filters, math, and edge cases.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Rendering ──────────────────────────────────────

async def test_template_literal_string(rest):
    """Template with just a literal returns the literal."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "hello world"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello world"


async def test_template_math_expression(rest):
    """Template evaluates math expressions."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 2 + 3 * 4 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "14"


async def test_template_float_division(rest):
    """Template float division with round works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ (10 / 3) | round(2) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3.33"


# ── State Functions ──────────────────────────────────────

async def test_template_states_function(rest):
    """states() returns the entity state."""
    await rest.set_state("sensor.tmpl_test", "42.5")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tmpl_test') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42.5"


async def test_template_is_state_true(rest):
    """is_state() returns true when entity matches."""
    await rest.set_state("light.tmpl_test", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.tmpl_test', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "true"


async def test_template_is_state_false(rest):
    """is_state() returns false when entity doesn't match."""
    await rest.set_state("light.tmpl_test2", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.tmpl_test2', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "false"


async def test_template_state_attr(rest):
    """state_attr() returns entity attribute value."""
    await rest.set_state("climate.tmpl_test", "heat", {"temperature": 72})
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('climate.tmpl_test', 'temperature') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "72"


async def test_template_states_unknown(rest):
    """states() returns 'unknown' for nonexistent entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.definitely_nonexistent_xyz') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "unknown"


async def test_template_now_function(rest):
    """now() returns a timestamp string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ now() }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Should contain a date-like pattern
    assert "T" in resp.text or "20" in resp.text


# ── Filters ──────────────────────────────────────────────

async def test_template_float_filter(rest):
    """float filter converts string to float."""
    await rest.set_state("sensor.tmpl_str", "72.5")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tmpl_str') | float + 1.5 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "74.0"


async def test_template_int_filter(rest):
    """int filter converts string to integer."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '42' | int + 8 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "50"


async def test_template_round_filter(rest):
    """round filter rounds to specified precision."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3.14159 | round(2) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


async def test_template_default_filter(rest):
    """default filter provides fallback for undefined values."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ missing_var | default('N/A') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "N/A"


async def test_template_lower_upper_filters(rest):
    """lower and upper filters transform case."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'Hello' | lower }}-{{ 'World' | upper }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello-WORLD"


async def test_template_abs_filter(rest):
    """abs filter returns absolute value."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ -42 | abs | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_iif_filter(rest):
    """iif filter returns conditional value."""
    await rest.set_state("light.tmpl_iif", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.tmpl_iif', 'on') | iif('yes', 'no') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


# ── Conditional Logic ────────────────────────────────────

async def test_template_if_else(rest):
    """Template if/else conditional works."""
    await rest.set_state("sensor.tmpl_temp", "80")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% if states('sensor.tmpl_temp') | float > 75 %}hot{% else %}cool{% endif %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hot"


async def test_template_comparison_operators(rest):
    """Template supports comparison operators."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 10 > 5 }}-{{ 3 == 3 }}-{{ 1 != 2 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "true-true-true"


# ── Error Handling ───────────────────────────────────────

async def test_template_syntax_error_returns_400(rest):
    """Invalid template syntax returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ unclosed"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_template_empty_string(rest):
    """Empty template returns empty string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == ""
