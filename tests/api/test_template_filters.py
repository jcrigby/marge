"""
CTS -- Template Filter & Function Depth Tests

Exercises template filters (replace, trim, min, max, log, from_json,
to_json, regex_match), global functions (float, int, bool), and
filter chaining through POST /api/template.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── String Filters ────────────────────────────────────────

async def test_template_replace_filter(rest):
    """replace filter substitutes substrings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello world' | replace('world', 'marge') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello marge"


async def test_template_trim_filter(rest):
    """trim filter strips whitespace."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '  spaced  ' | trim }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "spaced"


# ── Math Filters ──────────────────────────────────────────

async def test_template_max_filter(rest):
    """max filter returns larger of two values."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 5 | max(10) | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "10"


async def test_template_min_filter(rest):
    """min filter returns smaller of two values."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 5 | min(10) | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "5"


async def test_template_log_filter_natural(rest):
    """log filter computes natural log (ln)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 1 | log | round(1) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"  # ln(1) = 0


async def test_template_log_filter_base10(rest):
    """log filter with base argument."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 100 | log(10) | round(1) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "2.0"  # log10(100) = 2


# ── JSON Filters ──────────────────────────────────────────

async def test_template_from_json_filter(rest):
    """from_json parses a JSON string into an object."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": '{{ \'{"a":1,"b":2}\' | from_json | attr("a") }}'},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "1"


async def test_template_from_json_nested(rest):
    """from_json handles nested objects."""
    await rest.set_state("sensor.json_test", '{"temp":72,"unit":"F"}')
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.json_test') | from_json | attr('temp') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "72"


# ── Global Functions ──────────────────────────────────────

async def test_template_float_function(rest):
    """float() converts string to float with default."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ float('3.14') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


async def test_template_float_function_default(rest):
    """float() uses default for non-numeric strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ float('abc', 0.0) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "0.0"


async def test_template_int_function(rest):
    """int() converts to integer."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ int('42') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_int_function_float_truncate(rest):
    """int() truncates float strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ int('3.7') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3"


async def test_template_bool_function_true(rest):
    """bool() returns true for truthy strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ bool('yes') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "true"


async def test_template_bool_function_false(rest):
    """bool() returns false for falsy strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ bool('no') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "false"


# ── Filter Chaining ───────────────────────────────────────

async def test_template_filter_chain_float_round(rest):
    """Chained filters: float + round."""
    await rest.set_state("sensor.chain_test", "72.3456")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.chain_test') | float | round(1) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "72.3"


async def test_template_filter_chain_int_abs(rest):
    """Chained filters: int + abs."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '-7' | int | abs | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "7"


async def test_template_filter_chain_default_upper(rest):
    """Chained: undefined variable default then upper."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ undef_var | default('fallback') | upper }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "FALLBACK"


# ── For Loop ──────────────────────────────────────────────

async def test_template_for_loop(rest):
    """Template for loop iteration works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% for i in range(3) %}{{ i }}{% endfor %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "012"


# ── Multi-line Templates ─────────────────────────────────

async def test_template_multiline(rest):
    """Multi-line template renders correctly."""
    tmpl = "line1\n{{ 2 + 3 }}\nline3"
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": tmpl},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "5" in resp.text
    assert "line1" in resp.text
    assert "line3" in resp.text


# ── iif Edge Cases ────────────────────────────────────────

async def test_template_iif_false_branch(rest):
    """iif returns false branch for falsy value."""
    await rest.set_state("light.iif_test_off", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.iif_test_off', 'on') | iif('yes', 'no') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "no"


# ── State Function Edge Cases ─────────────────────────────

async def test_template_state_attr_missing(rest):
    """state_attr for missing attribute returns empty."""
    await rest.set_state("sensor.attr_miss", "42")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('sensor.attr_miss', 'nonexistent') | default('none') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "none"
