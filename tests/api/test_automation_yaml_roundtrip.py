"""
CTS -- Automation YAML Roundtrip Tests

Tests automation YAML get/put endpoints and verifies that
automation configuration survives reload cycles.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_automation_yaml_not_empty(rest):
    """GET automation YAML returns non-empty content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.text) > 50


async def test_automation_yaml_contains_alias(rest):
    """Automation YAML contains alias fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert "alias" in resp.text


async def test_automation_yaml_contains_trigger(rest):
    """Automation YAML contains trigger definitions."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert "trigger" in resp.text


async def test_automation_yaml_contains_action(rest):
    """Automation YAML contains action definitions."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert "action" in resp.text


async def test_scene_yaml_contains_name(rest):
    """Scene YAML contains name fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "name" in resp.text


async def test_scene_yaml_contains_entities(rest):
    """Scene YAML contains entity definitions."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "entities" in resp.text


async def test_reload_then_list_consistent(rest):
    """Automation list is consistent before and after reload."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    before = resp1.json()
    before_ids = sorted([a["id"] for a in before])

    await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    after = resp2.json()
    after_ids = sorted([a["id"] for a in after])

    assert before_ids == after_ids


async def test_reload_count_matches_automations(rest):
    """Reload returns count matching number of automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )
    data = resp.json()
    count = data["automations_reloaded"]

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp2.json()
    assert count == len(autos)


async def test_check_config_returns_valid(rest):
    """check_config returns valid when config is good."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "valid"
