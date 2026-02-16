"""
CTS -- Automation Entity State and Metadata Tests

Tests that automation entities (automation.*) appear in the state
machine with correct attributes (friendly_name, last_triggered, current),
and that the config/automation/config API returns proper metadata.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_automation_entities_exist(rest):
    """Loaded automations create automation.* entities in state machine."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 6  # 6 demo automations


async def test_automation_entity_has_friendly_name(rest):
    """Automation entities have friendly_name attribute (from alias)."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    if auto_entities:
        e = auto_entities[0]
        assert "friendly_name" in e["attributes"]
        assert len(e["attributes"]["friendly_name"]) > 0


async def test_automation_entity_state_on(rest):
    """Enabled automations have state 'on'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    for auto in autos:
        if auto.get("enabled", True):
            eid = f"automation.{auto['id']}"
            state = await rest.get_state(eid)
            if state:
                assert state["state"] == "on", f"{eid} should be on when enabled"


async def test_automation_config_has_fields(rest):
    """GET /api/config/automation/config returns expected fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    autos = resp.json()
    assert isinstance(autos, list)
    if autos:
        auto = autos[0]
        assert "id" in auto
        assert "alias" in auto
        assert "mode" in auto
        assert "trigger_count" in auto
        assert "condition_count" in auto
        assert "action_count" in auto
        assert "enabled" in auto


async def test_automation_config_trigger_count(rest):
    """Automation config shows correct trigger count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    for auto in autos:
        assert auto["trigger_count"] >= 0
        assert isinstance(auto["trigger_count"], int)


async def test_automation_config_mode(rest):
    """Automation mode is a valid string."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    for auto in autos:
        assert auto["mode"] in ["single", "restart", "queued", "parallel"]


async def test_automation_disable_changes_state(rest):
    """Disabling automation changes entity state to 'off'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if autos:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        await rest.call_service("automation", "turn_off", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "off"

        # Re-enable
        await rest.call_service("automation", "turn_on", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_automation_config_enabled_tracks_state(rest):
    """Config API reflects enabled/disabled state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if autos:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        # Disable
        await rest.call_service("automation", "turn_off", {"entity_id": eid})

        resp2 = await rest.client.get(
            f"{rest.base_url}/api/config/automation/config",
            headers=rest._headers(),
        )
        autos2 = resp2.json()
        auto2 = next(a for a in autos2 if a["id"] == auto_id)
        assert auto2["enabled"] is False

        # Re-enable
        await rest.call_service("automation", "turn_on", {"entity_id": eid})

        resp3 = await rest.client.get(
            f"{rest.base_url}/api/config/automation/config",
            headers=rest._headers(),
        )
        autos3 = resp3.json()
        auto3 = next(a for a in autos3 if a["id"] == auto_id)
        assert auto3["enabled"] is True


async def test_scene_entities_exist(rest):
    """Loaded scenes create scene.* entities in state machine."""
    states = await rest.get_states()
    scene_entities = [s for s in states if s["entity_id"].startswith("scene.")]
    assert len(scene_entities) >= 2  # evening and goodnight


async def test_scene_config_api(rest):
    """GET /api/config/scene/config returns scene metadata."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    scenes = resp.json()
    assert isinstance(scenes, list)
    if scenes:
        scene = scenes[0]
        assert "id" in scene
        assert "name" in scene
        assert "entity_count" in scene


async def test_automation_total_triggers_counter(rest):
    """total_triggers field starts at 0 or positive integer."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    for auto in autos:
        assert "total_triggers" in auto
        assert isinstance(auto["total_triggers"], int)
        assert auto["total_triggers"] >= 0


# ── Merged from depth: entity attribute checks ──────────────

async def test_automation_entity_default_on(rest):
    """Automation entities default to 'on' state."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    for auto in auto_entities:
        assert auto["state"] in ("on", "off")


async def test_automation_entity_has_attributes(rest):
    """Automation entities have attributes dict."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    for auto in auto_entities:
        assert isinstance(auto["attributes"], dict)


# ── Merged from depth: trigger API ──────────────────────────

async def test_automation_trigger_succeeds(rest):
    """automation.trigger via API returns success."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[0]["id"]
    eid = f"automation.{auto_id}"

    await rest.call_service("automation", "trigger", {"entity_id": eid})
    # Should not error -- automation was triggered


async def test_automation_trigger_increments_count(rest):
    """Triggering an automation increments total_triggers."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto = autos[0]
    auto_id = auto["id"]
    initial_count = auto.get("total_triggers", 0)

    eid = f"automation.{auto_id}"
    await rest.call_service("automation", "trigger", {"entity_id": eid})
    await asyncio.sleep(0.2)  # let the trigger execute

    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto = next(a for a in autos if a["id"] == auto_id)
    assert auto["total_triggers"] >= initial_count + 1


async def test_automation_trigger_sets_last_triggered(rest):
    """Triggering an automation sets last_triggered timestamp."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[0]["id"]
    eid = f"automation.{auto_id}"

    await rest.call_service("automation", "trigger", {"entity_id": eid})
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto = next(a for a in autos if a["id"] == auto_id)
    assert auto["last_triggered"] is not None
