"""
CTS -- Template State-Aware Function Tests

Tests minijinja template functions that access the state machine:
states(), is_state(), state_attr(), now(), and combinations with
filters. Uses POST /api/template to render templates.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def render(rest, template: str) -> str:
    """Helper: render a template via REST API."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    assert resp.status_code == 200, f"Template error: {resp.text}"
    return resp.text


# ── states() function ────────────────────────────────────

async def test_states_returns_current_value(rest):
    """states('entity_id') returns current state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_states_{tag}"
    await rest.set_state(eid, "42.5")

    result = await render(rest, f"{{{{ states('{eid}') }}}}")
    assert result.strip() == "42.5"


async def test_states_unknown_entity(rest):
    """states() for nonexistent entity returns 'unknown'."""
    result = await render(rest, "{{ states('sensor.tpl_never_existed_999') }}")
    assert result.strip() in ("unknown", "")


async def test_states_in_arithmetic(rest):
    """states() value used in arithmetic via float filter."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_arith_{tag}"
    await rest.set_state(eid, "10")

    result = await render(rest, f"{{{{ states('{eid}') | float + 5 }}}}")
    assert "15" in result.strip()


# ── is_state() function ─────────────────────────────────

async def test_is_state_true(rest):
    """is_state returns true when state matches."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tpl_is_{tag}"
    await rest.set_state(eid, "on")

    result = await render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert result.strip().lower() == "true"


async def test_is_state_false(rest):
    """is_state returns false when state doesn't match."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tpl_isf_{tag}"
    await rest.set_state(eid, "off")

    result = await render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert result.strip().lower() == "false"


async def test_is_state_nonexistent(rest):
    """is_state for nonexistent entity returns false."""
    result = await render(rest, "{{ is_state('sensor.tpl_no_exist_999', 'on') }}")
    assert result.strip().lower() == "false"


# ── state_attr() function ───────────────────────────────

async def test_state_attr_returns_value(rest):
    """state_attr returns attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_attr_{tag}"
    await rest.set_state(eid, "val", {"unit": "°C", "friendly_name": f"Temp {tag}"})

    result = await render(rest, f"{{{{ state_attr('{eid}', 'unit') }}}}")
    assert "°C" in result.strip()


async def test_state_attr_friendly_name(rest):
    """state_attr returns friendly_name attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_fn_{tag}"
    await rest.set_state(eid, "val", {"friendly_name": f"My Sensor {tag}"})

    result = await render(rest, f"{{{{ state_attr('{eid}', 'friendly_name') }}}}")
    assert f"My Sensor {tag}" in result.strip()


async def test_state_attr_missing(rest):
    """state_attr for missing attribute returns empty/none."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_noattr_{tag}"
    await rest.set_state(eid, "val")

    result = await render(rest, f"{{{{ state_attr('{eid}', 'nonexistent') }}}}")
    assert result.strip() in ("", "none", "None")


# ── now() function ───────────────────────────────────────

async def test_now_returns_timestamp(rest):
    """now() returns a timestamp-like string."""
    result = await render(rest, "{{ now() }}")
    assert "20" in result  # Year prefix
    assert ":" in result   # Time separator


# ── Filter chains with state data ────────────────────────

async def test_states_with_round_filter(rest):
    """states() | float | round produces rounded value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_round_{tag}"
    await rest.set_state(eid, "23.456")

    result = await render(rest, f"{{{{ states('{eid}') | float | round(1) }}}}")
    assert "23.5" in result.strip()


async def test_states_with_default_filter(rest):
    """states() | default provides fallback for missing entity."""
    result = await render(
        rest,
        "{{ states('sensor.tpl_fallback_999') | default('N/A') }}",
    )
    # Should return "N/A" or "unknown" (depends on states() returning unknown or empty)
    stripped = result.strip()
    assert stripped in ("N/A", "unknown")


async def test_conditional_template(rest):
    """if/else in template works with state data."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tpl_cond_{tag}"
    await rest.set_state(eid, "on")

    result = await render(
        rest,
        f"{{% if is_state('{eid}', 'on') %}}bright{{% else %}}dark{{% endif %}}",
    )
    assert result.strip() == "bright"


async def test_template_with_int_global_function(rest):
    """int() global function converts state to integer."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_int_{tag}"
    await rest.set_state(eid, "42")

    result = await render(rest, f"{{{{ int(states('{eid}')) + 8 }}}}")
    assert "50" in result.strip()


async def test_template_with_bool_global_function(rest):
    """bool() global function evaluates truthy values."""
    result = await render(rest, "{{ bool('true') }}")
    assert result.strip().lower() == "true"

    result2 = await render(rest, "{{ bool('off') }}")
    assert result2.strip().lower() == "false"
