"""
CTS -- Template State Composition Depth Tests

Tests complex template expressions combining state functions
(states, is_state, state_attr), conditionals, default handling,
and multi-entity compositions.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _render(rest, template):
    """Helper: render template and return stripped text."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.text.strip()


# ── Conditional Templates ──────────────────────────────────

async def test_template_if_state_on(rest):
    """Template with if/else based on entity state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tsc_if_{tag}"
    await rest.set_state(eid, "on")
    result = await _render(
        rest,
        f"{{% if states('{eid}') == 'on' %}}lit{{% else %}}dark{{% endif %}}",
    )
    assert result == "lit"


async def test_template_if_state_off(rest):
    """Template if/else returns else branch when off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tsc_ifoff_{tag}"
    await rest.set_state(eid, "off")
    result = await _render(
        rest,
        f"{{% if states('{eid}') == 'on' %}}lit{{% else %}}dark{{% endif %}}",
    )
    assert result == "dark"


# ── is_state Function ──────────────────────────────────────

async def test_is_state_true(rest):
    """is_state returns true when state matches."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.tsc_ist_{tag}"
    await rest.set_state(eid, "on")
    result = await _render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert result.lower() == "true"


async def test_is_state_false(rest):
    """is_state returns false when state doesn't match."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.tsc_isf_{tag}"
    await rest.set_state(eid, "off")
    result = await _render(rest, f"{{{{ is_state('{eid}', 'on') }}}}")
    assert result.lower() == "false"


# ── state_attr Function ───────────────────────────────────

async def test_state_attr_returns_value(rest):
    """state_attr returns the attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_attr_{tag}"
    await rest.set_state(eid, "42", {"unit": "W", "location": "garage"})
    result = await _render(rest, f"{{{{ state_attr('{eid}', 'unit') }}}}")
    assert result == "W"


async def test_state_attr_numeric(rest):
    """state_attr returns numeric attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tsc_brt_{tag}"
    await rest.set_state(eid, "on", {"brightness": 200})
    result = await _render(rest, f"{{{{ state_attr('{eid}', 'brightness') }}}}")
    assert "200" in result


# ── Arithmetic with State Values ───────────────────────────

async def test_state_arithmetic(rest):
    """Template arithmetic with state values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_math_{tag}"
    await rest.set_state(eid, "25")
    result = await _render(rest, f"{{{{ states('{eid}') | int * 4 }}}}")
    assert result == "100"


async def test_state_attr_arithmetic(rest):
    """Template arithmetic with attribute values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_amath_{tag}"
    await rest.set_state(eid, "42", {"offset": 8})
    result = await _render(
        rest,
        f"{{{{ states('{eid}') | int + state_attr('{eid}', 'offset') | int }}}}",
    )
    assert result == "50"


# ── Multi-Entity Compositions ──────────────────────────────

async def test_multi_entity_sum(rest):
    """Template summing states from multiple entities."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.tsc_sum1_{tag}"
    eid2 = f"sensor.tsc_sum2_{tag}"
    await rest.set_state(eid1, "30")
    await rest.set_state(eid2, "12")
    result = await _render(
        rest,
        f"{{{{ states('{eid1}') | int + states('{eid2}') | int }}}}",
    )
    assert result == "42"


async def test_multi_entity_comparison(rest):
    """Template comparing states of two entities."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.tsc_cmp1_{tag}"
    eid2 = f"sensor.tsc_cmp2_{tag}"
    await rest.set_state(eid1, "100")
    await rest.set_state(eid2, "50")
    result = await _render(
        rest,
        f"{{% if states('{eid1}') | int > states('{eid2}') | int %}}bigger{{% else %}}smaller{{% endif %}}",
    )
    assert result == "bigger"


# ── Default Handling ───────────────────────────────────────

async def test_states_nonexistent_returns_unknown(rest):
    """states() on non-existent entity returns 'unknown'."""
    tag = uuid.uuid4().hex[:8]
    result = await _render(
        rest,
        f"{{{{ states('sensor.no_such_{tag}') }}}}",
    )
    assert result == "unknown"


async def test_state_attr_nonexistent_with_default(rest):
    """state_attr on non-existent attribute with default."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_noattr_{tag}"
    await rest.set_state(eid, "42")
    result = await _render(
        rest,
        f"{{{{ state_attr('{eid}', 'missing_attr') | default('none') }}}}",
    )
    assert result == "none"


# ── String Operations on States ────────────────────────────

async def test_state_lower_filter(rest):
    """Template applies lower filter to state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_lower_{tag}"
    await rest.set_state(eid, "HELLO")
    result = await _render(rest, f"{{{{ states('{eid}') | lower }}}}")
    assert result == "hello"


async def test_state_replace_filter(rest):
    """Template applies replace filter to state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_repl_{tag}"
    await rest.set_state(eid, "hello world")
    result = await _render(
        rest,
        f"{{{{ states('{eid}') | replace('world', 'marge') }}}}",
    )
    assert result == "hello marge"


# ── now() Function ─────────────────────────────────────────

async def test_now_returns_timestamp(rest):
    """now() returns an ISO-like timestamp string."""
    result = await _render(rest, "{{ now() }}")
    assert "20" in result  # year 20xx
    assert "T" in result or "-" in result


# ── Chained State Operations ──────────────────────────────

async def test_chain_state_round_default(rest):
    """Chain: states → float → round → int."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tsc_chain_{tag}"
    await rest.set_state(eid, "3.14159")
    result = await _render(
        rest,
        f"{{{{ states('{eid}') | float | round(2) }}}}",
    )
    assert result == "3.14"
