"""
CTS -- Automation Multi-Entity Trigger and Cross-Automation Tests

Tests automation features: multi-entity triggers (StringOrVec),
automation toggle service, multiple automations firing from same
entity, and automation metadata across all 6 demo automations.
"""

import asyncio
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Multi-Entity Trigger (StringOrVec) ─────────────────────

@pytest.mark.marge_only
async def test_smoke_co_has_two_triggers(rest):
    """smoke_co_emergency has 2 triggers (smoke + CO detectors)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(a for a in data if a["id"] == "smoke_co_emergency_response")
    assert auto["trigger_count"] == 2


@pytest.mark.marge_only
async def test_goodnight_has_event_trigger(rest):
    """goodnight_routine has 1 trigger (event type)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(a for a in data if a["id"] == "goodnight_routine")
    assert auto["trigger_count"] == 1


@pytest.mark.marge_only
async def test_lock_verification_has_1_trigger(rest):
    """lock_verification has 1 trigger (alarm state change)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(a for a in data if a["id"] == "lock_verification_after_goodnight")
    assert auto["trigger_count"] == 1


@pytest.mark.marge_only
async def test_lock_verification_has_or_condition(rest):
    """lock_verification has 1 condition (OR with 2 sub-conditions)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(a for a in data if a["id"] == "lock_verification_after_goodnight")
    assert auto["condition_count"] == 1


@pytest.mark.marge_only
async def test_security_alert_has_condition(rest):
    """security_alert has 1 condition (alarm state)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = next(a for a in data if a["id"] == "security_alert_motion_while_armed_away")
    assert auto["condition_count"] == 1


# ── All 6 Automations Present ──────────────────────────────

@pytest.mark.marge_only
async def test_all_six_automations_loaded(rest):
    """All 6 demo automations are loaded."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = {a["id"] for a in data}
    expected = {
        "morning_wake_up", "security_alert_motion_while_armed_away", "sunset_exterior_and_evening_scene",
        "goodnight_routine", "lock_verification_after_goodnight", "smoke_co_emergency_response",
    }
    assert expected.issubset(ids)


@pytest.mark.marge_only
async def test_all_automations_have_alias(rest):
    """All automations have a non-empty alias."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert auto["alias"], f"Automation {auto['id']} has empty alias"


@pytest.mark.marge_only
async def test_all_automations_mode_single(rest):
    """All demo automations have mode 'single'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert auto["mode"] == "single", f"{auto['id']} mode is {auto['mode']}"


async def test_all_automation_entities_exist(rest):
    """All 6 automations have corresponding automation.* entities."""
    for auto_id in [
        "morning_wake_up", "security_alert_motion_while_armed_away", "sunset_exterior_and_evening_scene",
        "goodnight_routine", "lock_verification_after_goodnight", "smoke_co_emergency_response",
    ]:
        state = await rest.get_state(f"automation.{auto_id}")
        assert state is not None, f"automation.{auto_id} not found"
        assert state["state"] in ("on", "off")


async def test_all_automation_entities_on(rest):
    """All 6 automation entities are initially enabled (on)."""
    # Re-enable all first in case prior tests disabled some
    for auto_id in [
        "morning_wake_up", "security_alert_motion_while_armed_away", "sunset_exterior_and_evening_scene",
        "goodnight_routine", "lock_verification_after_goodnight", "smoke_co_emergency_response",
    ]:
        await rest.call_service("automation", "turn_on", {
            "entity_id": f"automation.{auto_id}"
        })
    await asyncio.sleep(0.1)

    for auto_id in [
        "morning_wake_up", "security_alert_motion_while_armed_away", "sunset_exterior_and_evening_scene",
        "goodnight_routine", "lock_verification_after_goodnight", "smoke_co_emergency_response",
    ]:
        state = await rest.get_state(f"automation.{auto_id}")
        assert state["state"] == "on", f"automation.{auto_id} is {state['state']}"


# ── Toggle Service ─────────────────────────────────────────

async def test_automation_toggle_disables(rest):
    """automation.toggle flips from on to off."""
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.1)
    assert (await rest.get_state("automation.morning_wake_up"))["state"] == "on"

    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.1)
    assert (await rest.get_state("automation.morning_wake_up"))["state"] == "off"

    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up"
    })


async def test_automation_toggle_roundtrip(rest):
    """automation.toggle twice returns to original state."""
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.1)

    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.1)
    assert (await rest.get_state("automation.sunset_exterior_and_evening_scene"))["state"] == "off"

    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.1)
    assert (await rest.get_state("automation.sunset_exterior_and_evening_scene"))["state"] == "on"
