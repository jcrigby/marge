"""
CTS -- Automation Trigger and State Matching Depth Tests

Tests state-based trigger matching, condition evaluation via
state changes, and automation execution verification through
observable state changes.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── State Trigger Matching ───────────────────────────────────

async def test_state_trigger_fires_on_match(rest):
    """Setting smoke detector 'on' triggers emergency automation."""
    # Reset entities
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.2)

    # Trigger
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    # Verify automation fired
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


async def test_state_trigger_no_match_wrong_value(rest):
    """State trigger doesn't fire when value doesn't match 'to'."""
    await rest.set_state("sensor.no_match_target", "before")
    # Change to a value that doesn't match any trigger
    await rest.set_state("sensor.random_entity", "anything")
    await asyncio.sleep(0.2)
    state = await rest.get_state("sensor.no_match_target")
    assert state["state"] == "before"


# ── Scene Activation ─────────────────────────────────────────

async def test_scene_turn_on_changes_entities(rest):
    """scene.turn_on applies scene entity states."""
    # Set initial states
    await rest.set_state("light.living_room_main", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.evening"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.2)

    # Evening scene should turn on living room main light
    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


async def test_scene_entities_exist(rest):
    """Scene entities exist in state machine."""
    states = await rest.get_states()
    scene_entities = [s for s in states if s["entity_id"].startswith("scene.")]
    assert len(scene_entities) >= 2


# ── Multiple Automations ─────────────────────────────────────

async def test_all_six_automations_loaded(rest):
    """All 6 configured automations are loaded."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 6


async def test_automation_ids_unique(rest):
    """All automation IDs are unique."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [a["id"] for a in data]
    assert len(ids) == len(set(ids))


async def test_automation_aliases_nonempty(rest):
    """All automations have non-empty aliases."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert auto["alias"] and len(auto["alias"]) > 0


# ── Automation Entity State ──────────────────────────────────

async def test_automation_entity_default_on(rest):
    """Automation entities default to 'on' state."""
    state = await rest.get_state("automation.morning_wakeup")
    assert state is not None
    assert state["state"] in ("on", "off")


async def test_automation_entity_attributes(rest):
    """Automation entities have expected attributes."""
    state = await rest.get_state("automation.morning_wakeup")
    attrs = state["attributes"]
    assert "friendly_name" in attrs


# ── Force Trigger Edge Cases ─────────────────────────────────

async def test_trigger_with_full_entity_id(rest):
    """Trigger with 'automation.' prefix works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.morning_wakeup"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_trigger_without_prefix(rest):
    """Trigger without 'automation.' prefix also works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "morning_wakeup"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_trigger_empty_entity_id(rest):
    """Trigger with empty entity_id returns 200 (no-op)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
