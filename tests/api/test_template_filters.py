"""
CTS -- Template Filter & Function Depth Tests

Exercises template filters (replace, trim, min, max, log, from_json,
to_json, regex_match), global functions (float, int, bool), and
filter chaining through POST /api/template.
"""

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


# ── String Filters ────────────────────────────────────────

async def test_template_replace_filter(rest):
    """replace filter substitutes substrings."""
    resp = await _render(rest, "{{ 'hello world' | replace('world', 'marge') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "hello marge"


async def test_template_trim_filter(rest):
    """trim filter strips whitespace."""
    resp = await _render(rest, "{{ '  spaced  ' | trim }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "spaced"


# ── Math Filters ──────────────────────────────────────────

async def test_template_max_filter(rest):
    """max filter returns larger of two values."""
    resp = await _render(rest, "{{ 5 | max(10) | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "10"


async def test_template_min_filter(rest):
    """min filter returns smaller of two values."""
    resp = await _render(rest, "{{ 5 | min(10) | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "5"


async def test_template_log_filter_natural(rest):
    """log filter computes natural log (ln)."""
    resp = await _render(rest, "{{ 1 | log | round(1) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"  # ln(1) = 0


async def test_template_log_filter_base10(rest):
    """log filter with base argument."""
    resp = await _render(rest, "{{ 100 | log(10) | round(1) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "2.0"  # log10(100) = 2


# ── JSON Filters ──────────────────────────────────────────

async def test_template_from_json_filter(rest):
    """from_json parses a JSON string into an object."""
    resp = await _render(rest, '{{ \'{"a":1,"b":2}\' | from_json | attr("a") }}')
    assert resp.status_code == 200
    assert resp.text.strip() == "1"


async def test_template_from_json_nested(rest):
    """from_json handles nested objects."""
    await rest.set_state("sensor.json_test", '{"temp":72,"unit":"F"}')
    resp = await _render(rest, "{{ states('sensor.json_test') | from_json | attr('temp') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "72"


# ── Global Functions ──────────────────────────────────────

async def test_template_float_function(rest):
    """float() converts string to float with default."""
    resp = await _render(rest, "{{ float('3.14') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


async def test_template_float_function_default(rest):
    """float() uses default for non-numeric strings."""
    resp = await _render(rest, "{{ float('abc', 0.0) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"


async def test_template_int_function(rest):
    """int() converts to integer."""
    resp = await _render(rest, "{{ int('42') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_int_function_float_truncate(rest):
    """int() truncates float strings."""
    resp = await _render(rest, "{{ int('3.7') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "3"


@pytest.mark.parametrize("template,expected", [
    ("{{ bool('yes') }}", "true"),
    ("{{ bool('no') }}", "false"),
    ("{{ bool(1) }}", "true"),
])
async def test_template_bool_function(rest, template, expected):
    """bool() function converts to boolean."""
    resp = await _render(rest, template)
    assert resp.status_code == 200
    assert resp.text.strip().lower() == expected


# ── Filter Chaining ───────────────────────────────────────

async def test_template_filter_chain_float_round(rest):
    """Chained filters: float + round."""
    await rest.set_state("sensor.chain_test", "72.3456")
    resp = await _render(rest, "{{ states('sensor.chain_test') | float | round(1) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "72.3"


async def test_template_filter_chain_int_abs(rest):
    """Chained filters: int + abs."""
    resp = await _render(rest, "{{ '-7' | int | abs | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "7"


async def test_template_filter_chain_default_upper(rest):
    """Chained: undefined variable default then upper."""
    resp = await _render(rest, "{{ undef_var | default('fallback') | upper }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "FALLBACK"


# ── Merged from depth: Additional Filters ────────────────

async def test_filter_round_zero(rest):
    """round filter with 0 precision rounds to integer."""
    resp = await _render(rest, "{{ 3.7 | round(0) }}")
    assert resp.status_code == 200
    result = resp.text.strip()
    assert result in ["4", "4.0"]


async def test_filter_from_json_basic(rest):
    """from_json filter parses JSON string."""
    resp = await _render(rest, "{{ '{\"key\": \"val\"}' | from_json }}")
    assert resp.status_code == 200
    assert "key" in resp.text
    assert "val" in resp.text


async def test_filter_to_json(rest):
    """to_json filter serializes to JSON."""
    resp = await _render(rest, "{{ 42 | to_json }}")
    assert resp.status_code == 200
    assert "42" in resp.text.strip()


async def test_chained_filters_trim_lower_replace(rest):
    """Multiple filters chained: trim + lower + replace."""
    resp = await _render(rest, "{{ '  Hello World  ' | trim | lower | replace('hello', 'hi') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "hi world"


async def test_string_concatenation(rest):
    """String concatenation with ~."""
    resp = await _render(rest, "{{ 'hello' ~ ' ' ~ 'world' }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "hello world"


# ── Merged from depth: For Loop ──────────────────────────

async def test_template_for_loop(rest):
    """Template for loop iteration works."""
    resp = await _render(rest, "{% for i in range(3) %}{{ i }}{% endfor %}")
    assert resp.status_code == 200
    assert resp.text.strip() == "012"


# ── Merged from depth: Multi-line ────────────────────────

async def test_template_multiline(rest):
    """Multi-line template renders correctly."""
    tmpl = "line1\n{{ 2 + 3 }}\nline3"
    resp = await _render(rest, tmpl)
    assert resp.status_code == 200
    assert "5" in resp.text
    assert "line1" in resp.text
    assert "line3" in resp.text


# ── Merged from depth: Math in Template ──────────────────

async def test_math_in_template(rest):
    """Math operations in templates."""
    resp = await _render(rest, "{{ (10 + 20) * 2 }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "60"
