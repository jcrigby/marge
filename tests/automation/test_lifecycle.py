"""
CTS -- Automation Lifecycle Tests

Tests automation enable/disable/toggle, listing metadata,
reload, and disabled-automation blocking.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── List Automations ─────────────────────────────────────

@pytest.mark.marge_only
async def test_list_automations(rest):
    """GET /api/config/automation/config returns all 6 automations."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    autos = resp.json()
    assert isinstance(autos, list)
    assert len(autos) >= 6
    ids = [a["id"] for a in autos]
    assert "morning_wake_up" in ids
    assert "sunset_exterior_and_evening_scene" in ids
    assert "goodnight_routine" in ids


@pytest.mark.marge_only
async def test_automation_info_fields(rest):
    """Automation info includes all expected metadata fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    morning = next(a for a in autos if a["id"] == "morning_wake_up")
    assert "alias" in morning
    assert "mode" in morning
    assert "trigger_count" in morning
    assert "action_count" in morning
    assert "enabled" in morning
    assert morning["enabled"] is True


# ── Enable/Disable/Toggle ───────────────────────────────

async def test_automation_disable(rest):
    """automation.turn_off disables an automation."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.morning_wake_up",
    })
    state = await rest.get_state("automation.morning_wake_up")
    assert state is not None
    assert state["state"] == "off"


async def test_automation_enable(rest):
    """automation.turn_on re-enables an automation."""
    # Ensure disabled first
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.morning_wake_up",
    })
    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up",
    })
    state = await rest.get_state("automation.morning_wake_up")
    assert state is not None
    assert state["state"] == "on"


async def test_automation_toggle(rest):
    """automation.toggle flips the enabled state."""
    # Start from known on state
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up",
    })
    state_before = await rest.get_state("automation.morning_wake_up")
    assert state_before["state"] == "on"

    # Toggle off
    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.morning_wake_up",
    })
    state_after = await rest.get_state("automation.morning_wake_up")
    assert state_after["state"] == "off"

    # Toggle back on
    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.morning_wake_up",
    })
    state_restored = await rest.get_state("automation.morning_wake_up")
    assert state_restored["state"] == "on"


# ── Disabled Automation Blocking ─────────────────────────

async def test_disabled_automation_does_not_fire(rest):
    """A disabled automation should not execute its actions."""
    import asyncio

    # Disable goodnight routine
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.goodnight_routine",
    })

    # Set preconditions
    await rest.set_state("light.bedroom", "on")
    await asyncio.sleep(0.1)

    # Fire the event that would normally trigger goodnight
    await rest.fire_event("bedside_button_pressed")
    await asyncio.sleep(0.3)

    # Light should still be on — automation was disabled
    bed = await rest.get_state("light.bedroom")
    assert bed["state"] == "on", "Disabled automation should not turn off lights"

    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.goodnight_routine",
    })


# ── Reload ───────────────────────────────────────────────

@pytest.mark.marge_only
async def test_reload_automations(rest):
    """POST /api/config/core/reload reloads automations from disk."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
    assert data["automations_reloaded"] >= 6


@pytest.mark.marge_only
async def test_reload_via_automation_path(rest):
    """POST /api/config/automation/reload also reloads automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"


# ── Force Trigger ────────────────────────────────────────

@pytest.mark.marge_only
async def test_force_trigger_sets_last_triggered(rest):
    """Force-triggering an automation updates its last_triggered."""
    import asyncio

    # Ensure enabled
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up",
    })

    # Set preconditions
    await rest.set_state("light.bedroom", "off")
    await rest.set_state("switch.coffee_maker", "off")
    await asyncio.sleep(0.1)

    # Force trigger
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up",
    })
    await asyncio.sleep(0.2)

    # Check automation info for last_triggered
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    morning = next(a for a in autos if a["id"] == "morning_wake_up")
    assert morning["last_triggered"] is not None
    assert morning["total_triggers"] >= 1


@pytest.mark.marge_only
async def test_trigger_count_increments(rest):
    """Each force-trigger increments total_triggers counter."""
    import asyncio

    # Get current count
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    morning = next(a for a in autos if a["id"] == "morning_wake_up")
    count_before = morning["total_triggers"]

    # Set preconditions and trigger
    await rest.set_state("light.bedroom", "off")
    await rest.set_state("switch.coffee_maker", "off")
    await asyncio.sleep(0.1)

    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up",
    })
    await asyncio.sleep(0.2)

    # Count should have increased
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    morning = next(a for a in autos if a["id"] == "morning_wake_up")
    assert morning["total_triggers"] > count_before
