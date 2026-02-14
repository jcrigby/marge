"""
CTS -- Automation API Depth Tests

Tests automation listing, individual info, YAML read/write,
and force trigger edge cases through the REST API.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Listing ────────────────────────────────────

async def test_automation_list_returns_list(rest):
    """GET /api/automations returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6  # 6 loaded automations


async def test_automation_list_has_id_and_alias(rest):
    """Automation entries have id and alias fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "id" in auto
    assert "alias" in auto
    assert len(auto["alias"]) > 0


async def test_automation_list_has_counts(rest):
    """Automation entries include trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "trigger_count" in auto
    assert "condition_count" in auto
    assert "action_count" in auto
    assert auto["trigger_count"] >= 1
    assert auto["action_count"] >= 1


async def test_automation_list_has_mode(rest):
    """Automation entries include mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    modes = [a["mode"] for a in data]
    assert "single" in modes


async def test_automation_list_has_enabled(rest):
    """Automation entries include enabled field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "enabled" in auto


# ── Automation YAML Read ──────────────────────────────────

async def test_automation_yaml_read(rest):
    """GET /api/config/automation/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    # Should contain YAML automation content
    assert "id:" in text or "alias:" in text


# ── Scene YAML Read ──────────────────────────────────────

async def test_scene_yaml_read(rest):
    """GET /api/config/scene/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    assert "id:" in text or "name:" in text


# ── Force Trigger ─────────────────────────────────────────

async def test_trigger_nonexistent_automation(rest):
    """Triggering nonexistent automation returns empty result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.does_not_exist"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Automation Entities ──────────────────────────────────

async def test_automation_entities_exist(rest):
    """Automation entities exist in state machine."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 6


async def test_automation_entity_has_friendly_name(rest):
    """Automation entities have friendly_name attribute (from alias)."""
    state = await rest.get_state("automation.morning_wakeup")
    assert state is not None
    assert "friendly_name" in state["attributes"]
    assert len(state["attributes"]["friendly_name"]) > 0
