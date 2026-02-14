"""
CTS -- Template Engine Depth Tests

Tests template rendering via REST /api/template: math operations,
string filters, state functions, conditional logic, type coercion,
edge cases, and filter chains.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Math ─────────────────────────────────────────────────

async def test_template_addition(rest):
    """Template addition."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 5 + 3 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "8"


async def test_template_multiplication(rest):
    """Template multiplication."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 7 * 6 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_division(rest):
    """Template division."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 100 / 4 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "25" in resp.text.strip()


async def test_template_modulo(rest):
    """Template modulo."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 17 % 5 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "2"


# ── String Filters ───────────────────────────────────────

async def test_template_upper(rest):
    """Template upper filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' | upper }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "HELLO"


async def test_template_lower(rest):
    """Template lower filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'WORLD' | lower }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "world"


async def test_template_title(rest):
    """Template title filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello world' | title }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "Hello World"


async def test_template_trim(rest):
    """Template trim filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '  spaced  ' | trim }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "spaced"


async def test_template_replace(rest):
    """Template replace filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello world' | replace('world', 'rust') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello rust"


# ── Type Coercion ────────────────────────────────────────

async def test_template_int_filter(rest):
    """Template int filter converts string to int."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '42' | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_float_filter(rest):
    """Template float filter converts string to float."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '3.14' | float }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "3.14" in resp.text.strip()


async def test_template_round_filter(rest):
    """Template round filter rounds to specified precision."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3.14159 | round(2) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "3.14"


# ── State Functions ──────────────────────────────────────

async def test_template_states_function(rest):
    """Template states() function reads entity state."""
    await rest.set_state("sensor.tmpl_depth_fn", "72")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tmpl_depth_fn') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "72"


async def test_template_is_state_true(rest):
    """Template is_state returns True when matching."""
    await rest.set_state("sensor.tmpl_depth_is", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('sensor.tmpl_depth_is', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_template_is_state_false(rest):
    """Template is_state returns False when not matching."""
    await rest.set_state("sensor.tmpl_depth_isf", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('sensor.tmpl_depth_isf', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_template_state_attr(rest):
    """Template state_attr() reads attribute."""
    await rest.set_state("sensor.tmpl_depth_attr", "50", {"unit": "kWh"})
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('sensor.tmpl_depth_attr', 'unit') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "kWh"


# ── Conditionals ─────────────────────────────────────────

async def test_template_if_true(rest):
    """Template if/else evaluates true branch."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'yes' if 2 > 1 else 'no' }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


async def test_template_if_false(rest):
    """Template if/else evaluates false branch."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'yes' if 1 > 2 else 'no' }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "no"


# ── Concatenation ────────────────────────────────────────

async def test_template_tilde_concat(rest):
    """Template ~ operator concatenates strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'a' ~ 'b' ~ 'c' }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "abc"


# ── Now Function ─────────────────────────────────────────

async def test_template_now(rest):
    """Template now() returns a timestamp-like string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ now() }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "20" in resp.text  # contains year 20xx


# ── iif Filter ───────────────────────────────────────────

async def test_template_iif_true(rest):
    """Template iif filter returns true value."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ true | iif('on', 'off') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "on"


async def test_template_iif_false(rest):
    """Template iif filter returns false value."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ false | iif('on', 'off') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "off"


# ── Length Filter ────────────────────────────────────────

async def test_template_length(rest):
    """Template length filter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' | length }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "5"


# ── Default Filter ───────────────────────────────────────

async def test_template_default(rest):
    """Template default filter provides fallback."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ undefined_var | default('fallback') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "fallback"
