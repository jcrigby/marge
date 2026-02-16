"""
CTS -- Template Engine Tests via REST API

Tests POST /api/template with filters (int, float, round, default, iif,
lower, upper, trim, replace, abs, max, min, from_json, to_json, log,
is_defined, length, title), state-aware functions (states, is_state,
state_attr, now), global functions (float, int, bool), filter chaining,
conditionals, loops, and error handling.
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


# ── Basic Arithmetic (parametrized) ──────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ 1 + 2 }}", "3"),
    ("{{ 5 + 3 }}", "8"),
    ("{{ 7 * 6 }}", "42"),
    ("{{ 100 / 4 }}", "25"),
    ("{{ 17 % 5 }}", "2"),
    ("{{ (10 + 20) * 2 }}", "60"),
    ("{{ (10 + 5) * 2 }}", "30"),
])
async def test_template_arithmetic(rest, template, expected):
    """Template arithmetic operations."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert expected in r.text.strip()


async def test_template_float_division(rest):
    """Template with float division."""
    r = await _render(rest, "{{ 10 / 3 }}")
    assert r.status_code == 200
    assert "3.3" in r.text


# ── String Filters (parametrized) ────────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ 'HELLO' | lower }}", "hello"),
    ("{{ 'WORLD' | lower }}", "world"),
    ("{{ 'hello' | upper }}", "HELLO"),
    ("{{ 'hello world' | title }}", "Hello World"),
])
async def test_filter_string_case(rest, template, expected):
    """String case filters: lower, upper, title."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert r.text.strip() == expected


async def test_filter_trim(rest):
    """trim filter removes whitespace."""
    r = await _render(rest, "{{ '  spaced  ' | trim }}")
    assert r.status_code == 200
    assert r.text.strip() == "spaced"


async def test_filter_replace(rest):
    """replace filter substitutes text."""
    r = await _render(rest, "{{ 'hello world' | replace('world', 'marge') }}")
    assert r.status_code == 200
    assert r.text.strip() == "hello marge"


async def test_filter_length(rest):
    """length filter returns string length."""
    r = await _render(rest, "{{ 'hello' | length }}")
    assert r.status_code == 200
    assert r.text.strip() == "5"


# ── Numeric Filters (parametrized) ───────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ '42' | int }}", "42"),
    ("{{ '3.14' | float }}", "3.14"),
    ("{{ -42 | abs }}", "42"),
])
async def test_filter_numeric_conversion(rest, template, expected):
    """Numeric conversion filters: int, float, abs."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert expected in r.text


async def test_filter_int_from_float_string(rest):
    """int filter on non-integer string returns 0 (parse failure)."""
    r = await _render(rest, "{{ '3.7' | int }}")
    assert r.status_code == 200
    assert "0" in r.text


@pytest.mark.parametrize("template,expected", [
    ("{{ 3.7 | round }}", "4"),
    ("{{ 3.14159 | round(2) }}", "3.14"),
    ("{{ 3.7 | round(0) }}", ["4", "4.0"]),
])
async def test_filter_round(rest, template, expected):
    """round filter with default and explicit precision."""
    r = await _render(rest, template)
    assert r.status_code == 200
    if isinstance(expected, list):
        assert r.text.strip() in expected
    else:
        assert expected in r.text


@pytest.mark.parametrize("template,expected", [
    ("{{ 3 | max(7) }}", "7"),
    ("{{ 3 | min(7) }}", "3"),
    ("{{ 5 | max(10) | int }}", "10"),
    ("{{ 5 | min(10) | int }}", "5"),
])
async def test_filter_min_max(rest, template, expected):
    """min/max filters return correct extreme."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert expected in r.text


@pytest.mark.parametrize("template,expected", [
    ("{{ 1 | log }}", "0"),
    ("{{ 1 | log | round(1) }}", "0.0"),
    ("{{ 100 | log(10) | round(1) }}", "2.0"),
])
async def test_filter_log(rest, template, expected):
    """log filter: natural log and base-10."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert expected in r.text


# ── Conditional Filters ──────────────────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ 1 | iif('yes', 'no') }}", "yes"),
    ("{{ 0 | iif('yes', 'no') }}", "no"),
    ("{{ true | iif('on', 'off') }}", "on"),
    ("{{ false | iif('on', 'off') }}", "off"),
    ("{{ '' | iif('yes', 'no') }}", "no"),
])
async def test_filter_iif(rest, template, expected):
    """iif filter returns correct branch for truthy/falsy input."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert r.text.strip() == expected


async def test_filter_default_undefined(rest):
    """default filter provides fallback for undefined."""
    r = await _render(rest, "{{ undefined_var | default('fallback') }}")
    assert r.status_code == 200
    assert r.text.strip() == "fallback"


async def test_filter_default_with_value(rest):
    """default filter returns value when defined."""
    r = await _render(rest, "{{ 'hello' | default('fallback') }}")
    assert r.status_code == 200
    assert r.text.strip() == "hello"


async def test_filter_is_defined(rest):
    """is_defined returns true for defined values."""
    r = await _render(rest, "{{ 42 | is_defined }}")
    assert r.status_code == 200
    assert r.text.strip() == "true"


# ── JSON Filters ─────────────────────────────────────────

async def test_filter_from_json_attr(rest):
    """from_json parses JSON string and attr accesses fields."""
    r = await _render(rest, '{{ \'{"a":1,"b":2}\' | from_json | attr("a") }}')
    assert r.status_code == 200
    assert r.text.strip() == "1"


async def test_filter_from_json_basic(rest):
    """from_json filter parses JSON string."""
    r = await _render(rest, "{{ '{\"key\": \"val\"}' | from_json }}")
    assert r.status_code == 200
    assert "key" in r.text
    assert "val" in r.text


async def test_filter_from_json_with_state(rest):
    """from_json handles JSON stored in entity state."""
    await rest.set_state("sensor.json_test", '{"temp":72,"unit":"F"}')
    r = await _render(rest, "{{ states('sensor.json_test') | from_json | attr('temp') }}")
    assert r.status_code == 200
    assert r.text.strip() == "72"


async def test_filter_to_json(rest):
    """to_json serializes value to string."""
    r = await _render(rest, "{{ 42 | to_json }}")
    assert r.status_code == 200
    assert "42" in r.text


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


async def test_states_with_float_comparison(rest):
    """states() | float > threshold works."""
    await rest.set_state("sensor.tmpl_adv_temp", "80")
    r = await _render(rest, "{{ states('sensor.tmpl_adv_temp') | float > 75 }}")
    assert r.status_code == 200
    assert r.text.strip() == "true"


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


async def test_fn_int_from_float_string(rest):
    """int() global function truncates float string."""
    r = await _render(rest, "{{ int('3.9') }}")
    assert r.status_code == 200
    assert r.text.strip() == "3"


async def test_fn_int_default(rest):
    """int() with invalid input uses default."""
    r = await _render(rest, "{{ int('abc', 99) }}")
    assert r.status_code == 200
    assert r.text.strip() == "99"


@pytest.mark.parametrize("val,expected", [
    ("true", "true"),
    ("yes", "true"),
    ("on", "true"),
    ("1", "true"),
    ("false", "false"),
    ("no", "false"),
    ("off", "false"),
    ("0", "false"),
])
async def test_fn_bool(rest, val, expected):
    """bool() function converts to boolean for truthy/falsy string values."""
    r = await _render(rest, f"{{{{ bool('{val}') }}}}")
    assert r.status_code == 200
    assert r.text.strip().lower() == expected, f"bool('{val}') should be {expected}"


async def test_fn_bool_numeric(rest):
    """bool() returns true for numeric 1."""
    r = await _render(rest, "{{ bool(1) }}")
    assert r.status_code == 200
    assert r.text.strip().lower() == "true"


# ── Error Handling ────────────────────────────────────────

async def test_template_syntax_error(rest):
    """Invalid template syntax returns 400."""
    r = await _render(rest, "{{ unclosed")
    assert r.status_code == 400


async def test_template_undefined_function(rest):
    """Undefined function in template returns 400."""
    r = await _render(rest, "{{ nonexistent_function() }}")
    assert r.status_code == 400


# ── Conditionals ─────────────────────────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ 'yes' if 2 > 1 else 'no' }}", "yes"),
    ("{{ 'yes' if 1 > 2 else 'no' }}", "no"),
])
async def test_template_conditional(rest, template, expected):
    """Template if/else evaluates correct branch."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert r.text.strip() == expected


async def test_template_conditional_with_is_state(rest):
    """Ternary-style if/else with is_state in template."""
    await rest.set_state("light.tmpl_adv_cond", "on")
    r = await _render(rest, "{{ 'active' if is_state('light.tmpl_adv_cond', 'on') else 'inactive' }}")
    assert r.status_code == 200
    assert r.text.strip() == "active"


# ── String Operations ────────────────────────────────────

@pytest.mark.parametrize("template,expected", [
    ("{{ 'a' ~ 'b' ~ 'c' }}", "abc"),
    ("{{ 'hello' ~ ' ' ~ 'world' }}", "hello world"),
])
async def test_template_tilde_concat(rest, template, expected):
    """Template ~ operator concatenates strings."""
    r = await _render(rest, template)
    assert r.status_code == 200
    assert r.text.strip() == expected


# ── iif with State ───────────────────────────────────────

async def test_template_iif_with_is_state(rest):
    """iif returns false branch for falsy is_state result."""
    await rest.set_state("light.iif_test_off", "off")
    r = await _render(rest, "{{ is_state('light.iif_test_off', 'on') | iif('yes', 'no') }}")
    assert r.status_code == 200
    assert r.text.strip() == "no"


# ── state_attr Edge Cases ────────────────────────────────

async def test_template_state_attr_missing(rest):
    """state_attr for missing attribute returns empty with default."""
    await rest.set_state("sensor.attr_miss", "42")
    r = await _render(rest, "{{ state_attr('sensor.attr_miss', 'nonexistent') | default('none') }}")
    assert r.status_code == 200
    assert r.text.strip() == "none"


# ── For Loop ─────────────────────────────────────────────

async def test_template_for_loop(rest):
    """Template for loop iteration works."""
    r = await _render(rest, "{% for i in range(3) %}{{ i }}{% endfor %}")
    assert r.status_code == 200
    assert r.text.strip() == "012"


# ── Multi-line Templates ─────────────────────────────────

async def test_template_multiline(rest):
    """Multi-line template renders correctly."""
    tmpl = "line1\n{{ 2 + 3 }}\nline3"
    r = await _render(rest, tmpl)
    assert r.status_code == 200
    assert "5" in r.text
    assert "line1" in r.text
    assert "line3" in r.text


# ── Filter Chaining ──────────────────────────────────────

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


async def test_filter_chain_trim_float_round_int(rest):
    """Chaining multiple filters: trim + float + round + int."""
    r = await _render(rest, "{{ '  42.7  ' | trim | float | round(0) | int }}")
    assert r.status_code == 200
    assert r.text.strip() == "43"


async def test_filter_chain_float_round_precision(rest):
    """Chained filters: float + round with precision 1."""
    await rest.set_state("sensor.chain_test", "72.3456")
    r = await _render(rest, "{{ states('sensor.chain_test') | float | round(1) }}")
    assert r.status_code == 200
    assert r.text.strip() == "72.3"


async def test_filter_chain_int_abs(rest):
    """Chained filters: int + abs."""
    r = await _render(rest, "{{ '-7' | int | abs | int }}")
    assert r.status_code == 200
    assert r.text.strip() == "7"


async def test_filter_chain_default_upper(rest):
    """Chained: undefined variable default then upper."""
    r = await _render(rest, "{{ undef_var | default('fallback') | upper }}")
    assert r.status_code == 200
    assert r.text.strip() == "FALLBACK"


async def test_filter_chain_trim_lower_replace(rest):
    """Multiple filters chained: trim + lower + replace."""
    r = await _render(rest, "{{ '  Hello World  ' | trim | lower | replace('hello', 'hi') }}")
    assert r.status_code == 200
    assert r.text.strip() == "hi world"
