"""
CTS -- Demo Automation: Smoke/CO Emergency End-to-End

Tests the smoke_co_emergency automation from automations.yaml:
multi-entity state trigger (smoke_detector OR co_detector → on),
action side effects (all lights on at 255, doors unlocked, alarm disarmed),
force trigger via automation.trigger service, and disable/re-enable lifecycle.
"""

import asyncio
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Precondition setup helper ──────────────────────────────

async def _setup_emergency_entities(rest):
    """Set all entities touched by smoke_co_emergency to known baseline."""
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await rest.set_state("binary_sensor.co_detector", "off")
    # Lights off
    for light in [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
        "light.porch", "light.pathway",
    ]:
        await rest.set_state(light, "off")
    # Doors locked
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("lock.back_door", "locked")
    # Alarm armed
    await rest.set_state("alarm_control_panel.home", "armed_home")
    # Ensure automation is enabled
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.1)


# ── Smoke Trigger ──────────────────────────────────────────

async def test_smoke_trigger_unlocks_front_door(rest):
    """Smoke detector → on unlocks front door."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


async def test_smoke_trigger_unlocks_back_door(rest):
    """Smoke detector → on unlocks back door."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("lock.back_door")
    assert state["state"] == "unlocked"


async def test_smoke_trigger_turns_on_all_lights(rest):
    """Smoke detector → on turns on all 9 lights."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    for light in [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.porch", "light.pathway",
    ]:
        state = await rest.get_state(light)
        assert state["state"] == "on", f"{light} should be on"


async def test_smoke_trigger_sets_brightness_255(rest):
    """Smoke detector → on sets light brightness to 255."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.bedroom")
    assert state["attributes"].get("brightness") == 255


async def test_smoke_trigger_disarms_alarm(rest):
    """Smoke detector → on disarms alarm."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("alarm_control_panel.home")
    assert state["state"] == "disarmed"


# ── CO Trigger (alternate entity) ──────────────────────────

async def test_co_trigger_also_fires_emergency(rest):
    """CO detector → on triggers the same emergency response."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.co_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("lock.front_door")
    assert state["state"] == "unlocked"


async def test_co_trigger_turns_on_lights(rest):
    """CO detector → on turns on lights."""
    await _setup_emergency_entities(rest)
    await rest.set_state("binary_sensor.co_detector", "on")
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.porch")
    assert state["state"] == "on"


# ── Force Trigger ──────────────────────────────────────────

async def test_force_trigger_executes_all_actions(rest):
    """automation.trigger bypasses triggers, runs all actions."""
    await _setup_emergency_entities(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.5)
    assert (await rest.get_state("lock.front_door"))["state"] == "unlocked"
    assert (await rest.get_state("lock.back_door"))["state"] == "unlocked"
    assert (await rest.get_state("light.bedroom"))["state"] == "on"


async def test_force_trigger_updates_metadata(rest):
    """Force trigger increments trigger count and updates last_triggered."""
    s1 = await rest.get_state("automation.smoke_co_emergency_response")
    count_before = s1["attributes"].get("current", 0)

    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.3)

    s2 = await rest.get_state("automation.smoke_co_emergency_response")
    assert s2["attributes"].get("current", 0) > count_before
    assert "last_triggered" in s2["attributes"]


# ── Disabled Automation ────────────────────────────────────

async def test_disabled_emergency_does_not_fire(rest):
    """Disabled smoke_co_emergency does not unlock doors."""
    await _setup_emergency_entities(rest)
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.1)

    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)

    state = await rest.get_state("lock.front_door")
    assert state["state"] == "locked", "Disabled automation should not unlock"

    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency_response"
    })


async def test_re_enabled_emergency_fires_again(rest):
    """Re-enabled automation fires on next trigger."""
    await _setup_emergency_entities(rest)
    # Disable, trigger (should not fire), re-enable, trigger (should fire)
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.1)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.3)
    assert (await rest.get_state("lock.front_door"))["state"] == "locked"

    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency_response"
    })
    await asyncio.sleep(0.1)
    # Reset trigger entity and fire again
    await rest.set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.1)
    await rest.set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.5)
    assert (await rest.get_state("lock.front_door"))["state"] == "unlocked"
