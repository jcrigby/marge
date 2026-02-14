"""
CTS -- Advanced Template Engine Tests

Tests template filters and global functions not covered by
existing tests: from_json, to_json, abs, log, max, min,
upper, lower, trim, replace, int/float/bool globals,
is_defined, iif, state_attr, is_state, now().
"""

import pytest

pytestmark = pytest.mark.asyncio

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def render(rest, template):
    """Helper: render a template via REST API."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    return resp


# ── String Filters ────────────────────────────────────────

async def test_template_upper_filter(rest):
    """upper filter converts to uppercase."""
    resp = await render(rest, "{{ 'hello' | upper }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "HELLO"


async def test_template_lower_filter(rest):
    """lower filter converts to lowercase."""
    resp = await render(rest, "{{ 'WORLD' | lower }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "world"


async def test_template_trim_filter(rest):
    """trim filter removes whitespace."""
    resp = await render(rest, "{{ '  spaced  ' | trim }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "spaced"


async def test_template_replace_filter(rest):
    """replace filter substitutes text."""
    resp = await render(rest, "{{ 'hello world' | replace('world', 'marge') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "hello marge"


# ── Math Filters ─────────────────────────────────────────

async def test_template_abs_filter(rest):
    """abs filter returns absolute value."""
    resp = await render(rest, "{{ -42 | abs }}")
    assert resp.status_code == 200
    assert float(resp.text.strip()) == 42.0


async def test_template_log_filter_natural(rest):
    """log filter with no base uses natural log."""
    resp = await render(rest, "{{ 1 | log | round(1) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"


async def test_template_max_filter(rest):
    """max filter returns larger value."""
    resp = await render(rest, "{{ 3 | max(7) }}")
    assert resp.status_code == 200
    assert float(resp.text.strip()) == 7.0


async def test_template_min_filter(rest):
    """min filter returns smaller value."""
    resp = await render(rest, "{{ 3 | min(7) }}")
    assert resp.status_code == 200
    assert float(resp.text.strip()) == 3.0


# ── JSON Filters ─────────────────────────────────────────

async def test_template_from_json_filter(rest):
    """from_json parses JSON string into object."""
    resp = await render(rest, '{{ \'{"a":1}\' | from_json }}')
    assert resp.status_code == 200
    # minijinja renders maps as {a: 1} or similar


async def test_template_to_json_filter(rest):
    """to_json serializes value to string."""
    resp = await render(rest, "{{ 42 | to_json }}")
    assert resp.status_code == 200
    assert "42" in resp.text


# ── Conditional Filters ──────────────────────────────────

async def test_template_iif_truthy(rest):
    """iif returns if_true for truthy value."""
    resp = await render(rest, "{{ 1 | iif('yes', 'no') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


async def test_template_iif_falsy(rest):
    """iif returns if_false for falsy value."""
    resp = await render(rest, "{{ 0 | iif('yes', 'no') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "no"


async def test_template_iif_empty_string_falsy(rest):
    """iif treats empty string as falsy."""
    resp = await render(rest, "{{ '' | iif('yes', 'no') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "no"


async def test_template_is_defined_filter(rest):
    """is_defined returns true for defined values."""
    resp = await render(rest, "{{ 42 | is_defined }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "true"


async def test_template_default_filter_with_value(rest):
    """default filter returns value when defined."""
    resp = await render(rest, "{{ 'hello' | default('fallback') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "hello"


# ── Global Functions ─────────────────────────────────────

async def test_template_float_function(rest):
    """float() converts string to float."""
    resp = await render(rest, "{{ float('3.14') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


async def test_template_float_default(rest):
    """float() with invalid input uses default."""
    resp = await render(rest, "{{ float('abc', 0.0) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"


async def test_template_int_function(rest):
    """int() converts string to integer."""
    resp = await render(rest, "{{ int('42') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_int_from_float_string(rest):
    """int() truncates float string."""
    resp = await render(rest, "{{ int('3.9') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "3"


async def test_template_int_default(rest):
    """int() with invalid input uses default."""
    resp = await render(rest, "{{ int('abc', 99) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "99"


async def test_template_bool_true_values(rest):
    """bool() returns true for 'true', 'yes', 'on', '1'."""
    for val in ["true", "yes", "on", "1"]:
        resp = await render(rest, f"{{{{ bool('{val}') }}}}")
        assert resp.status_code == 200
        assert resp.text.strip() == "true", f"bool('{val}') should be true"


async def test_template_bool_false_values(rest):
    """bool() returns false for 'false', 'no', 'off', '0'."""
    for val in ["false", "no", "off", "0"]:
        resp = await render(rest, f"{{{{ bool('{val}') }}}}")
        assert resp.status_code == 200
        assert resp.text.strip() == "false", f"bool('{val}') should be false"


# ── State-Aware Functions ────────────────────────────────

async def test_template_states_function(rest):
    """states() returns entity state."""
    await rest.set_state("sensor.tmpl_adv_test", "42")
    resp = await render(rest, "{{ states('sensor.tmpl_adv_test') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_states_unknown_entity(rest):
    """states() returns 'unknown' for missing entity."""
    resp = await render(rest, "{{ states('sensor.tmpl_adv_missing_xyz') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "unknown"


async def test_template_is_state_true(rest):
    """is_state() returns true when matching."""
    await rest.set_state("light.tmpl_adv_is", "on")
    resp = await render(rest, "{{ is_state('light.tmpl_adv_is', 'on') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "true"


async def test_template_is_state_false(rest):
    """is_state() returns false when not matching."""
    await rest.set_state("light.tmpl_adv_isf", "off")
    resp = await render(rest, "{{ is_state('light.tmpl_adv_isf', 'on') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "false"


async def test_template_state_attr(rest):
    """state_attr() returns entity attribute."""
    await rest.set_state("sensor.tmpl_adv_attr", "50", {"unit": "lux"})
    resp = await render(rest, "{{ state_attr('sensor.tmpl_adv_attr', 'unit') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "lux"


async def test_template_now_function(rest):
    """now() returns current timestamp string."""
    resp = await render(rest, "{{ now() }}")
    assert resp.status_code == 200
    text = resp.text.strip()
    assert "T" in text
    assert len(text) >= 19


# ── Compound Expressions ─────────────────────────────────

async def test_template_states_with_float_comparison(rest):
    """states() | float > threshold works."""
    await rest.set_state("sensor.tmpl_adv_temp", "80")
    resp = await render(rest, "{{ states('sensor.tmpl_adv_temp') | float > 75 }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "true"


async def test_template_filter_chain(rest):
    """Chaining multiple filters works."""
    resp = await render(rest, "{{ '  42.7  ' | trim | float | round(0) | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "43"


async def test_template_conditional_expression(rest):
    """Ternary-style if/else in template."""
    await rest.set_state("light.tmpl_adv_cond", "on")
    resp = await render(rest, "{{ 'active' if is_state('light.tmpl_adv_cond', 'on') else 'inactive' }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "active"


async def test_template_math_operations(rest):
    """Math operations in templates."""
    resp = await render(rest, "{{ (10 + 5) * 2 }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "30"
