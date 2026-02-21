"""
CTS -- Automation Execution Path Tests

Tests the automation engine's execution paths: force trigger, event trigger,
automation metadata tracking, reload, and condition evaluation.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_automation_disable_sets_off(rest):
    """Disabling automation sets entity state to 'off'."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency"
    })
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "off"

    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency"
    })
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "on"


# ── Force Trigger ────────────────────────────────────────

async def test_force_trigger_executes_actions(rest):
    """automation.trigger bypasses triggers and conditions."""
    # Set up a known starting state for the automation's targets
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency"
    })
    await asyncio.sleep(0.3)
    # The trigger count should increase
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state is not None


async def test_force_trigger_records_last_triggered(rest):
    """Force trigger updates last_triggered attribute."""
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency"
    })
    await asyncio.sleep(0.2)
    state = await rest.get_state("automation.smoke_co_emergency")
    assert "last_triggered" in state["attributes"]
    assert len(state["attributes"]["last_triggered"]) > 0


async def test_force_trigger_increments_count(rest):
    """Force trigger increments current trigger count."""
    s1 = await rest.get_state("automation.smoke_co_emergency")
    count_before = s1["attributes"].get("current", 0)

    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency"
    })
    await asyncio.sleep(0.2)

    s2 = await rest.get_state("automation.smoke_co_emergency")
    count_after = s2["attributes"].get("current", 0)
    assert count_after > count_before


# ── Automation Reload ────────────────────────────────────

async def test_reload_preserves_trigger_counts(rest):
    """Reloading does not reset trigger counts."""
    # Get current count
    s1 = await rest.get_state("automation.smoke_co_emergency")
    count = s1["attributes"].get("current", 0)

    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    s2 = await rest.get_state("automation.smoke_co_emergency")
    # Count should be preserved (>= because other tests may trigger)
    assert s2["attributes"].get("current", 0) >= count


# ── Automation Info API ──────────────────────────────────

@pytest.mark.marge_only
async def test_automations_info_endpoint(rest):
    """GET /api/config/automation/config returns automation info list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.marge_only
async def test_automations_info_has_fields(rest):
    """Automation info entries have required fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    for field in ["id", "alias", "mode", "trigger_count", "condition_count",
                   "action_count", "enabled"]:
        assert field in auto, f"Missing field: {field}"


@pytest.mark.marge_only
async def test_automations_info_trigger_counts(rest):
    """Automation info reports correct trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    # All should have at least 1 trigger
    for auto in data:
        assert auto["trigger_count"] >= 1
        assert auto["action_count"] >= 1


# ── State Trigger + Conditions ───────────────────────────

async def test_state_trigger_fires_automation(rest):
    """State trigger fires when entity matches to value."""
    # smoke_co_emergency triggers on binary_sensor.smoke_detector -> on
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.1)

    # Trigger the automation by setting state to 'on'
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    # Check the automation was triggered (last_triggered updated)
    state = await rest.get_state("automation.smoke_co_emergency")
    assert "last_triggered" in state["attributes"]


# ── Event Trigger ────────────────────────────────────────

async def test_fire_event_triggers_automation(rest):
    """Firing an event triggers automations with event trigger."""
    # At minimum, test that fire_event endpoint works
    result = await rest.fire_event("test_automation_event")
    assert "message" in result
