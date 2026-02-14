"""
CTS -- Template Advanced Filters Depth Tests

Tests template filters and global functions not covered by existing
depth tests: from_json, to_json, log, min, max, regex_match,
is_defined, bool(), float(default), int(default), filter chains.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _tpl(rest, template):
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    return resp


# ── from_json / to_json ─────────────────────────────────

async def test_from_json_filter(rest):
    """from_json filter parses JSON string."""
    resp = await _tpl(rest, """{{ '{"a":1}' | from_json }}""")
    assert resp.status_code == 200
    # minijinja renders map as something containing "a"
    assert "1" in resp.text


async def test_to_json_filter(rest):
    """to_json filter serializes value to JSON string."""
    resp = await _tpl(rest, "{{ 42 | to_json }}")
    assert resp.status_code == 200
    assert "42" in resp.text


# ── log filter ───────────────────────────────────────────

async def test_log_natural(rest):
    """log filter computes natural logarithm."""
    # ln(e^2) ~= 2.0
    resp = await _tpl(rest, "{{ 7.389056 | log | round(1) }}")
    assert resp.status_code == 200
    assert "2.0" in resp.text


async def test_log_base_10(rest):
    """log filter with base argument."""
    # log10(100) = 2
    resp = await _tpl(rest, "{{ 100 | log(10) | round(0) | int }}")
    assert resp.status_code == 200
    assert "2" in resp.text


# ── min / max filters ───────────────────────────────────

async def test_min_filter(rest):
    """min filter returns the smaller value."""
    resp = await _tpl(rest, "{{ 10 | min(5) | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "5"


async def test_max_filter(rest):
    """max filter returns the larger value."""
    resp = await _tpl(rest, "{{ 10 | max(20) | int }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "20"


# ── abs filter (with negative float) ────────────────────

async def test_abs_negative_float(rest):
    """abs filter on negative float."""
    resp = await _tpl(rest, "{{ -3.7 | abs | round(1) }}")
    assert resp.status_code == 200
    assert "3.7" in resp.text


# ── regex_match filter ───────────────────────────────────

async def test_regex_match_nonempty(rest):
    """regex_match returns truthy for non-empty string."""
    resp = await _tpl(rest, "{{ 'abc' | regex_match('a.*') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


# ── is_defined filter ───────────────────────────────────

async def test_is_defined_true(rest):
    """is_defined filter returns true for defined value."""
    resp = await _tpl(rest, "{{ 42 | is_defined }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_is_defined_false(rest):
    """is_defined filter returns false for undefined value."""
    resp = await _tpl(rest, "{{ undef_xyz | is_defined }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


# ── bool() global function ──────────────────────────────

async def test_bool_true_string(rest):
    """bool('true') returns true."""
    resp = await _tpl(rest, "{{ bool('true') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_bool_false_string(rest):
    """bool('false') returns false."""
    resp = await _tpl(rest, "{{ bool('false') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_bool_on_string(rest):
    """bool('on') returns true."""
    resp = await _tpl(rest, "{{ bool('on') }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_bool_zero(rest):
    """bool(0) returns false."""
    resp = await _tpl(rest, "{{ bool(0) }}")
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


# ── float() with default ────────────────────────────────

async def test_float_function_valid(rest):
    """float('3.14') returns 3.14."""
    resp = await _tpl(rest, "{{ float('3.14') }}")
    assert resp.status_code == 200
    assert "3.14" in resp.text


async def test_float_function_with_default(rest):
    """float('abc', 0.0) returns the default."""
    resp = await _tpl(rest, "{{ float('abc', 99.5) }}")
    assert resp.status_code == 200
    assert "99.5" in resp.text


# ── int() with default ──────────────────────────────────

async def test_int_function_valid(rest):
    """int('42') returns 42."""
    resp = await _tpl(rest, "{{ int('42') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_int_function_with_default(rest):
    """int('abc', 0) returns the default."""
    resp = await _tpl(rest, "{{ int('abc', -1) }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "-1"


async def test_int_from_float_string(rest):
    """int('3.9') truncates to 3."""
    resp = await _tpl(rest, "{{ int('3.9') }}")
    assert resp.status_code == 200
    assert resp.text.strip() == "3"


# ── Filter Chains ────────────────────────────────────────

async def test_filter_chain_float_round_int(rest):
    """Chaining float | round | int works."""
    resp = await _tpl(rest, "{{ '72.567' | float | round(1) }}")
    assert resp.status_code == 200
    assert "72.6" in resp.text


async def test_filter_chain_state_float_max(rest):
    """Chain: states() | float | max(threshold)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_chain_{tag}"
    await rest.set_state(eid, "25.0")
    resp = await _tpl(rest, f"{{{{ states('{eid}') | float | max(30) | int }}}}")
    assert resp.status_code == 200
    assert resp.text.strip() == "30"
