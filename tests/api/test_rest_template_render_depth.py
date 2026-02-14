"""
CTS -- REST Template Render Depth Tests

Tests POST /api/template endpoint: literal strings, arithmetic,
state-aware functions (states, is_state, state_attr), filters
(int, float, round, lower, upper, trim), error handling, and
variable substitution.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Literal Rendering ────────────────────────────────────

async def test_template_literal_string(rest):
    """POST /api/template renders literal text."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "hello world"},
    )
    assert resp.status_code == 200
    assert resp.text == "hello world"


async def test_template_arithmetic(rest):
    """POST /api/template renders arithmetic expressions."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 10 + 5 }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "15"


async def test_template_string_concatenation(rest):
    """POST /api/template concatenates strings."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 'foo' ~ 'bar' }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "foobar"


# ── State Functions ──────────────────────────────────────

async def test_template_states_function(rest):
    """Template states() reads entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rtrd_{tag}"
    await rest.set_state(eid, "99")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": f"{{{{ states('{eid}') }}}}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "99"


async def test_template_is_state_true(rest):
    """Template is_state() returns true when matches."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rtrd_is_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": f"{{{{ is_state('{eid}', 'on') }}}}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_template_is_state_false(rest):
    """Template is_state() returns false when not matching."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rtrd_isf_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": f"{{{{ is_state('{eid}', 'on') }}}}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_template_state_attr(rest):
    """Template state_attr() reads entity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rtrd_attr_{tag}"
    await rest.set_state(eid, "72", {"unit": "F"})

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": f"{{{{ state_attr('{eid}', 'unit') }}}}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "F"


async def test_template_now_function(rest):
    """Template now() returns current time string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ now() }}"},
    )
    assert resp.status_code == 200
    assert "20" in resp.text  # Contains year


# ── Filters ──────────────────────────────────────────────

async def test_template_int_filter(rest):
    """Template int filter converts to integer."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ '42' | int }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "42"


async def test_template_float_filter(rest):
    """Template float filter converts to float."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ '3.14' | float }}"},
    )
    assert resp.status_code == 200
    assert "3.14" in resp.text


async def test_template_lower_filter(rest):
    """Template lower filter lowercases."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 'HELLO' | lower }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello"


async def test_template_upper_filter(rest):
    """Template upper filter uppercases."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 'hello' | upper }}"},
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "HELLO"
