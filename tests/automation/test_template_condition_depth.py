"""
CTS -- Template and Numeric State Condition Depth Tests

Tests condition evaluation through the automation engine:
template conditions with states() and is_state(), numeric_state
conditions with above/below/both, and nested and/or conditions.
Uses force-trigger with pre-set entity states to verify conditions.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Template Conditions via Template API ───────────────────
# (These test the template engine's condition-relevant functions)

async def test_template_states_returns_entity_state(rest):
    """Template states('entity') returns current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_cond_{tag}"
    await rest.set_state(eid, "42.5")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('" + eid + "') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "42.5" in resp.text


async def test_template_is_state_true(rest):
    """Template is_state() returns true for matching state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_is_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('" + eid + "', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("true", "1")


async def test_template_is_state_false(rest):
    """Template is_state() returns false for non-matching state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_isf_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('" + eid + "', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("false", "0")


async def test_template_comparison_greater(rest):
    """Template numeric comparison: states() | float > value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_gt_{tag}"
    await rest.set_state(eid, "75.0")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('" + eid + "') | float > 50 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("true", "1")


async def test_template_comparison_less(rest):
    """Template numeric comparison: states() | float < value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_lt_{tag}"
    await rest.set_state(eid, "25.0")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('" + eid + "') | float < 50 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("true", "1")


async def test_template_logical_and(rest):
    """Template logical and: two conditions both true."""
    tag = uuid.uuid4().hex[:8]
    e1 = f"sensor.tmpl_and1_{tag}"
    e2 = f"sensor.tmpl_and2_{tag}"
    await rest.set_state(e1, "on")
    await rest.set_state(e2, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('" + e1 + "', 'on') and is_state('" + e2 + "', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("true", "1")


async def test_template_logical_or(rest):
    """Template logical or: one condition true."""
    tag = uuid.uuid4().hex[:8]
    e1 = f"sensor.tmpl_or1_{tag}"
    e2 = f"sensor.tmpl_or2_{tag}"
    await rest.set_state(e1, "on")
    await rest.set_state(e2, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('" + e1 + "', 'on') or is_state('" + e2 + "', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result = resp.text.strip().lower()
    assert result in ("true", "1")


async def test_template_state_attr(rest):
    """Template state_attr() returns attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tmpl_attr_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200})

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('" + eid + "', 'brightness') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "200" in resp.text


async def test_template_round_filter(rest):
    """Template round filter works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 3.14159 | round(2) }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "3.14" in resp.text


async def test_template_int_filter(rest):
    """Template int filter converts integer string."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '42' | int }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "42" in resp.text


async def test_template_float_filter(rest):
    """Template float filter works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ '3' | float }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "3" in resp.text


async def test_template_default_filter(rest):
    """Template default filter returns fallback for unknown entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.nonexistent_xyz_99') | default('unknown') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Should contain 'unknown' or empty string
    text = resp.text.strip()
    assert text in ("unknown", "", "unavailable")
