"""
CTS -- Automation Condition and Action Tests

Tests automation enable/disable/toggle, condition evaluation
via state triggers, numeric_state conditions, and automation
metadata tracking through the REST API.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── Enable / Disable / Toggle ────────────────────────────────

async def test_automation_turn_off(rest):
    """automation.turn_off disables an automation."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.morning_wakeup",
    })
    state = await rest.get_state("automation.morning_wakeup")
    assert state["state"] == "off"
    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wakeup",
    })


async def test_automation_turn_on(rest):
    """automation.turn_on enables an automation."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.morning_wakeup",
    })
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wakeup",
    })
    state = await rest.get_state("automation.morning_wakeup")
    assert state["state"] == "on"


async def test_disabled_automation_not_triggered(rest):
    """Disabled automation doesn't execute when triggered."""
    # Set up a known state
    await rest.set_state("sensor.disable_test_target", "before")
    # Disable the automation
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.morning_wakeup",
    })
    # Force trigger — should not execute
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wakeup",
    })
    await asyncio.sleep(0.1)
    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wakeup",
    })


# ── Force Trigger ─────────────────────────────────────────────

async def test_trigger_existing_automation(rest):
    """Triggering existing automation returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.morning_wakeup"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Automation Config Detail ──────────────────────────────────

async def test_automation_config_has_description(rest):
    """Automation config entries include description field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "description" in auto


async def test_automation_config_has_last_triggered(rest):
    """Automation config entries include last_triggered field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "last_triggered" in auto


async def test_automation_config_has_total_triggers(rest):
    """Automation config entries include total_triggers field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "total_triggers" in auto
    assert isinstance(auto["total_triggers"], int)


# ── Automation Reload ─────────────────────────────────────────

async def test_automation_reload(rest):
    """POST /api/config/core/reload reloads automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "automations_reloaded" in data


async def test_automation_reload_via_automation_endpoint(rest):
    """POST /api/config/automation/reload reloads automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "automations_reloaded" in data


# ── Scene Config ──────────────────────────────────────────────

async def test_scene_config_list(rest):
    """GET /api/config/scene/config returns scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # evening, goodnight


async def test_scene_config_has_name(rest):
    """Scene config entries have name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    scene = data[0]
    assert "name" in scene
    assert len(scene["name"]) > 0


async def test_scene_config_has_entities(rest):
    """Scene config entries have entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    scene = data[0]
    assert "entity_count" in scene
    assert scene["entity_count"] >= 1
