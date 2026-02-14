"""
CTS -- Condition Evaluation Edge Case Depth Tests

Tests automation condition evaluation edge cases: numeric_state boundary
values, nested Or/And conditions, template condition truthy values,
time condition ranges, and state condition on missing entities.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── NumericState Boundaries ──────────────────────────────

async def test_numeric_state_above_boundary(rest):
    """NumericState: value equal to 'above' threshold evaluates correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ns_bound_{tag}"
    await rest.set_state(eid, "50")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('ENTITY') | float > 50 }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    # 50 is NOT > 50, so should be false
    assert result is False or str(result).strip().lower() == "false"


async def test_numeric_state_below_boundary(rest):
    """NumericState: value equal to 'below' threshold evaluates correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ns_below_{tag}"
    await rest.set_state(eid, "100")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('ENTITY') | float < 100 }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    # 100 is NOT < 100, so should be false
    assert result is False or str(result).strip().lower() == "false"


async def test_numeric_state_between(rest):
    """NumericState: value between above and below is true."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ns_between_{tag}"
    await rest.set_state(eid, "75")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('ENTITY') | float > 50 and states('ENTITY') | float < 100 }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    assert result is True or str(result).strip().lower() == "true"


async def test_numeric_state_unparseable(rest):
    """NumericState: non-numeric state with default filter returns default or error."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ns_nan_{tag}"
    await rest.set_state(eid, "unavailable")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ states('ENTITY') | default('unknown') }}".replace("ENTITY", eid)},
    )
    # State is "unavailable" — default filter only applies if undefined
    assert resp.status_code == 200
    assert resp.text == "unavailable"


# ── Nested Or/And Conditions ─────────────────────────────

async def test_nested_or_conditions(rest):
    """Or condition with nested state checks via template."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.or_a_{tag}"
    eid2 = f"sensor.or_b_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('E1', 'on') or is_state('E2', 'on') }}".replace("E1", eid1).replace("E2", eid2)},
    )
    result = resp.json()
    assert result is True or str(result).strip().lower() == "true"


async def test_nested_and_conditions(rest):
    """And condition: all must be true."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.and_a_{tag}"
    eid2 = f"sensor.and_b_{tag}"
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('E1', 'on') and is_state('E2', 'on') }}".replace("E1", eid1).replace("E2", eid2)},
    )
    result = resp.json()
    assert result is True or str(result).strip().lower() == "true"


async def test_nested_and_fails_when_one_false(rest):
    """And condition: fails when one is false."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.andf_a_{tag}"
    eid2 = f"sensor.andf_b_{tag}"
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('E1', 'on') and is_state('E2', 'on') }}".replace("E1", eid1).replace("E2", eid2)},
    )
    result = resp.json()
    assert result is False or str(result).strip().lower() == "false"


# ── Template Condition Truthy Values ─────────────────────

async def test_template_true_literal(rest):
    """Template returning true when condition is met."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 1 == 1 }}"},
    )
    result = resp.json()
    assert result is True or str(result).strip().lower() == "true"


async def test_template_numeric_one(rest):
    """Template returning numeric 1."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 1 }}"},
    )
    result = resp.json()
    assert int(result) == 1


async def test_template_false_literal(rest):
    """Template returning false when condition not met."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 1 == 2 }}"},
    )
    result = resp.json()
    assert result is False or str(result).strip().lower() == "false"


# ── State Condition Edge Cases ────────────────────────────

async def test_state_condition_missing_entity(rest):
    """State condition on nonexistent entity is falsy."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.missing_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('ENTITY', 'on') }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    assert result is False or str(result).strip().lower() in ("false", "0", "")


async def test_state_condition_exact_match(rest):
    """State condition requires exact string match."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.exact_{tag}"
    await rest.set_state(eid, "ON")
    # "ON" != "on" — case-sensitive
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('ENTITY', 'on') }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    assert result is False or str(result).strip().lower() in ("false", "0")


async def test_state_condition_matches_exact(rest):
    """State condition matches when state is exactly the checked value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ematch_{tag}"
    await rest.set_state(eid, "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ is_state('ENTITY', 'on') }}".replace("ENTITY", eid)},
    )
    result = resp.json()
    assert result is True or str(result).strip().lower() in ("true", "1")
