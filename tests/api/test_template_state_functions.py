"""
CTS -- Template State Function Tests

Tests template rendering with state-aware functions:
states(), is_state(), state_attr(), and now().
Requires entities to be pre-set for the template context.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_states_function_returns_value(rest):
    """states('entity_id') returns current state value."""
    await rest.set_state("sensor.tpl_states", "72.5")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tpl_states') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "72.5"


async def test_states_unknown_entity(rest):
    """states() returns 'unknown' for nonexistent entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.does_not_exist_xyz') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "unknown"


async def test_is_state_true(rest):
    """is_state() returns true when state matches."""
    await rest.set_state("light.tpl_is_state", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.tpl_is_state', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_is_state_false(rest):
    """is_state() returns false when state doesn't match."""
    await rest.set_state("light.tpl_is_state2", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('light.tpl_is_state2', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_is_state_nonexistent(rest):
    """is_state() returns false for nonexistent entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ is_state('sensor.nonexistent_xyz', 'on') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "false"


async def test_state_attr_returns_value(rest):
    """state_attr() returns attribute value."""
    await rest.set_state("sensor.tpl_attr", "ok", {"unit": "celsius", "precision": 2})
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('sensor.tpl_attr', 'unit') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "celsius"


async def test_state_attr_numeric(rest):
    """state_attr() returns numeric attribute value."""
    await rest.set_state("sensor.tpl_attr_num", "ok", {"count": 42})
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('sensor.tpl_attr_num', 'count') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "42" in resp.text.strip()


async def test_state_attr_missing_attr(rest):
    """state_attr() for missing attribute returns none/empty."""
    await rest.set_state("sensor.tpl_attr_miss", "ok")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ state_attr('sensor.tpl_attr_miss', 'nonexistent') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Should return none, empty string, or "None"
    result = resp.text.strip().lower()
    assert result in ["", "none", "null", "undefined"]


async def test_now_function(rest):
    """now() returns current timestamp."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ now() }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "20" in resp.text  # Year 20xx


async def test_states_in_conditional(rest):
    """states() used in conditional template."""
    await rest.set_state("sensor.tpl_cond", "on")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% if states('sensor.tpl_cond') == 'on' %}yes{% else %}no{% endif %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


async def test_states_with_math(rest):
    """states() result used in arithmetic."""
    await rest.set_state("sensor.tpl_math", "25")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tpl_math') | float + 10 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "35" in resp.text.strip()


async def test_multiple_state_functions(rest):
    """Multiple state functions in one template."""
    await rest.set_state("sensor.tpl_multi_a", "hot")
    await rest.set_state("sensor.tpl_multi_b", "cold")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ states('sensor.tpl_multi_a') }} and {{ states('sensor.tpl_multi_b') }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "hot" in resp.text
    assert "cold" in resp.text


async def test_is_state_in_template_logic(rest):
    """is_state() in template if/else logic."""
    await rest.set_state("light.tpl_logic", "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% if is_state('light.tpl_logic', 'on') %}bright{% else %}dark{% endif %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "dark"
