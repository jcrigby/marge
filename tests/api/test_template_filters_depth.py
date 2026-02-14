"""
CTS -- Template Filter Depth Tests

Tests minijinja filter implementations: int, float, round, default,
lower, upper, trim, replace, regex_match, from_json, to_json,
log, abs, min, max, iif.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_filter_int(rest):
    """int filter converts to integer."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '42' | int }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "42"


async def test_filter_float(rest):
    """float filter converts to float."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '3.14' | float }}"},
        headers=rest._headers(),
    )
    assert "3.14" in resp.text.strip()


async def test_filter_round(rest):
    """round filter rounds to specified precision."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3.14159 | round(2) }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "3.14"


async def test_filter_round_zero(rest):
    """round filter with 0 precision rounds to integer."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3.7 | round(0) }}"},
        headers=rest._headers(),
    )
    result = resp.text.strip()
    assert result in ["4", "4.0"]


async def test_filter_default(rest):
    """default filter provides fallback for undefined."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ undefined_var | default('fallback') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "fallback"


async def test_filter_lower(rest):
    """lower filter converts to lowercase."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'HELLO' | lower }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "hello"


async def test_filter_upper(rest):
    """upper filter converts to uppercase."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' | upper }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "HELLO"


async def test_filter_trim(rest):
    """trim filter removes whitespace."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '  spaced  ' | trim }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "spaced"


async def test_filter_replace(rest):
    """replace filter substitutes text."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello world' | replace('world', 'marge') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "hello marge"


async def test_filter_abs(rest):
    """abs filter returns absolute value."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ -42 | abs }}"},
        headers=rest._headers(),
    )
    assert "42" in resp.text.strip()


async def test_filter_iif_true(rest):
    """iif filter returns true value when condition is true."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ true | iif('yes', 'no') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "yes"


async def test_filter_iif_false(rest):
    """iif filter returns false value when condition is false."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ false | iif('yes', 'no') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "no"


async def test_filter_from_json(rest):
    """from_json filter parses JSON string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '{\"key\": \"val\"}' | from_json }}"},
        headers=rest._headers(),
    )
    assert "key" in resp.text
    assert "val" in resp.text


async def test_filter_to_json(rest):
    """to_json filter serializes to JSON."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 42 | to_json }}"},
        headers=rest._headers(),
    )
    assert "42" in resp.text.strip()


async def test_filter_log(rest):
    """log filter computes natural logarithm."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 1 | log }}"},
        headers=rest._headers(),
    )
    assert "0" in resp.text.strip()


async def test_filter_max(rest):
    """max filter returns maximum of two values."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3 | max(5) }}"},
        headers=rest._headers(),
    )
    assert "5" in resp.text.strip()


async def test_filter_min(rest):
    """min filter returns minimum of two values."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3 | min(1) }}"},
        headers=rest._headers(),
    )
    assert "1" in resp.text.strip()


async def test_fn_float(rest):
    """float() function converts string to float."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ float('3.14') }}"},
        headers=rest._headers(),
    )
    assert "3.14" in resp.text.strip()


async def test_fn_int(rest):
    """int() function converts string to int."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ int('42') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "42"


async def test_fn_bool(rest):
    """bool() function converts to boolean."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ bool(1) }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip().lower() == "true"


async def test_chained_filters(rest):
    """Multiple filters chained together."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '  Hello World  ' | trim | lower | replace('hello', 'hi') }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "hi world"


async def test_math_in_template(rest):
    """Math operations in templates."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ (10 + 20) * 2 }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "60"


async def test_string_concatenation(rest):
    """String concatenation with ~."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' ~ ' ' ~ 'world' }}"},
        headers=rest._headers(),
    )
    assert resp.text.strip() == "hello world"
