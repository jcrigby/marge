"""
CTS -- Automation State Trigger Behavior Tests

Tests state-based trigger matching: 'to' value matching,
action execution verification, and trigger context.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_smoke_trigger_unlocks_door(rest):
    """Smoke detector on → unlocks front door (emergency automation)."""
    # Reset
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.3)

    # Trigger
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


async def test_non_matching_state_no_trigger(rest):
    """State change to non-matching value doesn't trigger."""
    # Set up a canary entity
    tag = "no_trigger_canary"
    await rest.set_state(f"sensor.{tag}", "unchanged")

    # Change some random entity that doesn't match any trigger
    await rest.set_state("sensor.random_no_match", "random_value")
    await asyncio.sleep(0.3)

    state = await rest.get_state(f"sensor.{tag}")
    assert state["state"] == "unchanged"


async def test_automation_entity_tracks_state(rest):
    """Automation entities reflect on/off state."""
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] in ["on", "off"]
    assert "friendly_name" in state["attributes"]


async def test_trigger_updates_last_triggered(rest):
    """Triggering updates last_triggered attribute."""
    eid = "automation.smoke_co_emergency"

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    lt = state["attributes"].get("last_triggered", "")
    assert len(lt) > 0
    assert "20" in lt  # Year 20xx


async def test_disabled_automation_state(rest):
    """Disabled automation has state 'off'."""
    eid = "automation.smoke_co_emergency"

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"

    # Re-enable
    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )


async def test_multiple_automations_exist(rest):
    """Multiple automation entities exist."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    states = resp.json()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 6


async def test_automation_friendly_name(rest):
    """Automation entities have friendly_name from alias."""
    state = await rest.get_state("automation.morning_wakeup")
    assert "friendly_name" in state["attributes"]
    assert len(state["attributes"]["friendly_name"]) > 0


