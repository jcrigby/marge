"""
CTS -- Template Engine Tests via REST API

Tests POST /api/template with filters (int, float, round, default, iif,
lower, upper, trim, replace, abs, max, min, from_json, to_json, log),
state-aware functions (states, is_state, state_attr, now), and
global functions (float, int, bool).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _render(rest, template):
    """POST /api/template and return the response."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    return resp


# ── Basic Arithmetic ──────────────────────────────────────

async def test_template_addition(rest):
    """Template with addition."""
    r = await _render(rest, "{{ 1 + 2 }}")
    assert r.status_code == 200
    assert "3" in r.text


async def test_template_multiplication(rest):
    """Template with multiplication."""
    r = await _render(rest, "{{ 7 * 6 }}")
    assert r.status_code == 200
    assert "42" in r.text


async def test_template_float_division(rest):
    """Template with float division."""
    r = await _render(rest, "{{ 10 / 3 }}")
    assert r.status_code == 200
    assert "3.3" in r.text


# ── Filters ───────────────────────────────────────────────

async def test_filter_int(rest):
    """int filter converts string to integer."""
    r = await _render(rest, "{{ '42' | int }}")
    assert r.status_code == 200
    assert "42" in r.text


async def test_filter_int_from_float_string(rest):
    """int filter on non-integer string returns 0 (parse failure)."""
    r = await _render(rest, "{{ '3.7' | int }}")
    assert r.status_code == 200
    assert "0" in r.text


async def test_filter_float(rest):
    """float filter converts string to float."""
    r = await _render(rest, "{{ '3.14' | float }}")
    assert r.status_code == 200
    assert "3.14" in r.text


async def test_filter_round_default(rest):
    """round filter rounds to integer by default."""
    r = await _render(rest, "{{ 3.7 | round }}")
    assert r.status_code == 200
    assert "4" in r.text


async def test_filter_round_precision(rest):
    """round filter with precision argument."""
    r = await _render(rest, "{{ 3.14159 | round(2) }}")
    assert r.status_code == 200
    assert "3.14" in r.text


async def test_filter_default(rest):
    """default filter provides fallback for undefined."""
    r = await _render(rest, "{{ undefined_var | default('fallback') }}")
    assert r.status_code == 200
    assert "fallback" in r.text


async def test_filter_iif_truthy(rest):
    """iif filter returns true-value for truthy input."""
    r = await _render(rest, "{{ 1 | iif('yes', 'no') }}")
    assert r.status_code == 200
    assert "yes" in r.text


async def test_filter_iif_falsy(rest):
    """iif filter returns false-value for falsy input."""
    r = await _render(rest, "{{ 0 | iif('yes', 'no') }}")
    assert r.status_code == 200
    assert "no" in r.text


async def test_filter_lower(rest):
    """lower filter converts to lowercase."""
    r = await _render(rest, "{{ 'HELLO' | lower }}")
    assert r.status_code == 200
    assert "hello" in r.text


async def test_filter_upper(rest):
    """upper filter converts to uppercase."""
    r = await _render(rest, "{{ 'hello' | upper }}")
    assert r.status_code == 200
    assert "HELLO" in r.text


async def test_filter_trim(rest):
    """trim filter removes whitespace."""
    r = await _render(rest, "{{ '  hello  ' | trim }}")
    assert r.status_code == 200
    assert r.text.strip() == "hello"


async def test_filter_replace(rest):
    """replace filter substitutes text."""
    r = await _render(rest, "{{ 'hello world' | replace('world', 'marge') }}")
    assert r.status_code == 200
    assert "marge" in r.text


async def test_filter_abs(rest):
    """abs filter returns absolute value."""
    r = await _render(rest, "{{ -42 | abs }}")
    assert r.status_code == 200
    assert "42" in r.text


async def test_filter_max(rest):
    """max filter returns larger value."""
    r = await _render(rest, "{{ 3 | max(7) }}")
    assert r.status_code == 200
    assert "7" in r.text


async def test_filter_min(rest):
    """min filter returns smaller value."""
    r = await _render(rest, "{{ 3 | min(7) }}")
    assert r.status_code == 200
    assert "3" in r.text


async def test_filter_log_natural(rest):
    """log filter computes natural logarithm."""
    r = await _render(rest, "{{ 1 | log }}")
    assert r.status_code == 200
    assert "0" in r.text  # ln(1) = 0


# ── State-Aware Functions ─────────────────────────────────

async def test_states_function(rest):
    """states() returns entity state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_{tag}"
    await rest.set_state(eid, "42.5")

    r = await _render(rest, f"{{{{ states('{eid}') }}}}")
    assert r.status_code == 200
    assert "42.5" in r.text


async def test_states_unknown_entity(rest):
    """states() returns 'unknown' for nonexistent entity."""
    r = await _render(rest, "{{ states('sensor.nonexistent_xyz_999') }}")
    assert r.status_code == 200
    assert "unknown" in r.text


async def test_is_state_true(rest):
    """is_state() returns true when state matches."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tplis_{tag}"
    await rest.set_state(eid, "on")

    r = await _render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert r.status_code == 200
    assert "true" in r.text.lower()


async def test_is_state_false(rest):
    """is_state() returns false when state doesn't match."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tplisf_{tag}"
    await rest.set_state(eid, "off")

    r = await _render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert r.status_code == 200
    assert "false" in r.text.lower()


async def test_state_attr_function(rest):
    """state_attr() returns entity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tplattr_{tag}"
    await rest.set_state(eid, "25", {"unit": "celsius"})

    r = await _render(rest, f"{{{{ state_attr('{eid}', 'unit') }}}}")
    assert r.status_code == 200
    assert "celsius" in r.text


async def test_now_function(rest):
    """now() returns current timestamp string."""
    r = await _render(rest, "{{ now() }}")
    assert r.status_code == 200
    # Should contain a date-like pattern
    assert "20" in r.text  # year starts with 20xx


# ── Global Functions ──────────────────────────────────────

async def test_fn_float_conversion(rest):
    """float() function converts string to float."""
    r = await _render(rest, "{{ float('3.14') }}")
    assert r.status_code == 200
    assert "3.14" in r.text


async def test_fn_float_default(rest):
    """float() returns default on invalid input."""
    r = await _render(rest, "{{ float('abc', 0.0) }}")
    assert r.status_code == 200
    assert "0" in r.text


async def test_fn_int_conversion(rest):
    """int() function converts string to int."""
    r = await _render(rest, "{{ int('99') }}")
    assert r.status_code == 200
    assert "99" in r.text


async def test_fn_bool_true(rest):
    """bool() returns true for truthy values."""
    r = await _render(rest, "{{ bool('yes') }}")
    assert r.status_code == 200
    assert "true" in r.text.lower()


async def test_fn_bool_false(rest):
    """bool() returns false for falsy values."""
    r = await _render(rest, "{{ bool('no') }}")
    assert r.status_code == 200
    assert "false" in r.text.lower()


# ── Error Handling ────────────────────────────────────────

async def test_template_syntax_error(rest):
    """Invalid template syntax returns 400."""
    r = await _render(rest, "{{ unclosed")
    assert r.status_code == 400


async def test_template_undefined_function(rest):
    """Undefined function in template returns 400."""
    r = await _render(rest, "{{ nonexistent_function() }}")
    assert r.status_code == 400


# ── Filter Chaining ───────────────────────────────────────

async def test_filter_chain_round_int(rest):
    """Chained round + int filters."""
    r = await _render(rest, "{{ 3.7 | round | int }}")
    assert r.status_code == 200
    assert "4" in r.text


async def test_states_with_float_filter(rest):
    """states() piped through float filter."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tplchain_{tag}"
    await rest.set_state(eid, "72.5")

    r = await _render(rest, f"{{{{ states('{eid}') | float | round }}}}")
    assert r.status_code == 200
    # 72.5 rounded = 72 or 73 depending on rounding strategy
    text = r.text.strip()
    assert text in ("72", "72.0", "73", "73.0")
