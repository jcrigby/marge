"""
CTS -- Demo Automation: Security Alert, Lock Verification, Goodnight

Tests three demo automations from automations.yaml:
1. security_alert — condition-gated (armed_away only), motion trigger
2. lock_verification — OR condition (any door unlocked), armed_night trigger
3. goodnight_routine — event trigger (bedside_button_pressed)
"""

import asyncio
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Security Alert ─────────────────────────────────────────

async def _setup_security(rest):
    """Baseline for security_alert tests."""
    await rest.set_state("binary_sensor.entryway_motion", "off")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.security_alert_motion_while_armed_away"
    })
    await asyncio.sleep(0.1)


async def test_security_alert_fires_when_armed_away(rest):
    """Motion while armed_away triggers security alert."""
    await _setup_security(rest)
    await rest.set_state("alarm_control_panel.home", "armed_away")
    await asyncio.sleep(0.1)

    await rest.set_state("binary_sensor.entryway_motion", "on")
    await asyncio.sleep(0.5)

    # Automation should have fired (check trigger count)
    state = await rest.get_state("automation.security_alert_motion_while_armed_away")
    assert state is not None
    assert state["attributes"].get("current", 0) >= 1


async def test_security_alert_blocked_when_armed_home(rest):
    """Motion while armed_home does NOT trigger alert (condition fails)."""
    await _setup_security(rest)
    await rest.set_state("alarm_control_panel.home", "armed_home")
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.security_alert_motion_while_armed_away")
    count_before = s1["attributes"].get("current", 0)

    await rest.set_state("binary_sensor.entryway_motion", "on")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.security_alert_motion_while_armed_away")
    assert s2["attributes"].get("current", 0) == count_before


async def test_security_alert_blocked_when_disarmed(rest):
    """Motion while disarmed does NOT trigger alert."""
    await _setup_security(rest)
    await rest.set_state("alarm_control_panel.home", "disarmed")
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.security_alert_motion_while_armed_away")
    count_before = s1["attributes"].get("current", 0)

    # Reset motion then trigger
    await rest.set_state("binary_sensor.entryway_motion", "off")
    await asyncio.sleep(0.1)
    await rest.set_state("binary_sensor.entryway_motion", "on")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.security_alert_motion_while_armed_away")
    assert s2["attributes"].get("current", 0) == count_before


# ── Lock Verification ──────────────────────────────────────

async def _setup_lock_verification(rest):
    """Baseline for lock_verification tests."""
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.lock_verification_after_goodnight"
    })
    await asyncio.sleep(0.1)


async def test_lock_verify_fires_when_door_unlocked(rest):
    """Alarm → armed_night with unlocked door triggers notification."""
    await _setup_lock_verification(rest)
    # Set one door unlocked
    await rest.set_state("lock.front_door", "unlocked")
    await rest.set_state("lock.back_door", "locked")
    await rest.set_state("alarm_control_panel.home", "armed_home")
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.lock_verification_after_goodnight")
    count_before = s1["attributes"].get("current", 0)

    # Trigger: alarm goes to armed_night
    await rest.set_state("alarm_control_panel.home", "armed_night")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.lock_verification_after_goodnight")
    assert s2["attributes"].get("current", 0) > count_before


async def test_lock_verify_fires_when_back_door_unlocked(rest):
    """OR condition: back door unlocked also triggers."""
    await _setup_lock_verification(rest)
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("lock.back_door", "unlocked")
    await rest.set_state("alarm_control_panel.home", "armed_home")
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.lock_verification_after_goodnight")
    count_before = s1["attributes"].get("current", 0)

    await rest.set_state("alarm_control_panel.home", "armed_night")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.lock_verification_after_goodnight")
    assert s2["attributes"].get("current", 0) > count_before


async def test_lock_verify_skipped_when_all_locked(rest):
    """All doors locked: lock_verification does NOT fire."""
    await _setup_lock_verification(rest)
    await rest.set_state("lock.front_door", "locked")
    await rest.set_state("lock.back_door", "locked")
    await rest.set_state("alarm_control_panel.home", "armed_home")
    await asyncio.sleep(0.1)

    s1 = await rest.get_state("automation.lock_verification_after_goodnight")
    count_before = s1["attributes"].get("current", 0)

    await rest.set_state("alarm_control_panel.home", "armed_night")
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.lock_verification_after_goodnight")
    assert s2["attributes"].get("current", 0) == count_before


# ── Goodnight Routine ──────────────────────────────────────

async def _setup_goodnight(rest):
    """Baseline for goodnight_routine tests."""
    # Lights on, doors unlocked, alarm disarmed
    for light in [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
        "light.porch", "light.pathway",
    ]:
        await rest.set_state(light, "on")
    await rest.set_state("lock.front_door", "unlocked")
    await rest.set_state("lock.back_door", "unlocked")
    await rest.set_state("climate.thermostat", "heat", {"temperature": 72})
    await rest.set_state("alarm_control_panel.home", "disarmed")
    await rest.set_state("media_player.living_room", "playing")
    await rest.set_state("switch.coffee_maker", "on")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.1)


async def test_goodnight_force_trigger_turns_off_lights(rest):
    """Force-triggering goodnight turns off all lights."""
    await _setup_goodnight(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.5)

    for light in ["light.bedroom", "light.kitchen", "light.porch"]:
        state = await rest.get_state(light)
        assert state["state"] == "off", f"{light} should be off"


async def test_goodnight_force_trigger_locks_doors(rest):
    """Force-triggering goodnight locks both doors."""
    await _setup_goodnight(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.5)

    assert (await rest.get_state("lock.front_door"))["state"] == "locked"
    assert (await rest.get_state("lock.back_door"))["state"] == "locked"


async def test_goodnight_force_trigger_arms_night(rest):
    """Force-triggering goodnight arms alarm for night."""
    await _setup_goodnight(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.5)

    state = await rest.get_state("alarm_control_panel.home")
    assert state["state"] == "armed_night"


async def test_goodnight_force_trigger_lowers_thermostat(rest):
    """Force-triggering goodnight sets thermostat to 66."""
    await _setup_goodnight(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.5)

    state = await rest.get_state("climate.thermostat")
    assert state["attributes"].get("temperature") == 66


async def test_goodnight_force_trigger_stops_media(rest):
    """Force-triggering goodnight turns off media player."""
    await _setup_goodnight(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.goodnight_routine"
    })
    await asyncio.sleep(0.5)

    state = await rest.get_state("media_player.living_room")
    assert state["state"] == "off"


async def test_goodnight_event_trigger_fires(rest):
    """Firing bedside_button_pressed event triggers goodnight."""
    await _setup_goodnight(rest)

    s1 = await rest.get_state("automation.goodnight_routine")
    count_before = s1["attributes"].get("current", 0)

    result = await rest.fire_event("bedside_button_pressed")
    assert "message" in result
    await asyncio.sleep(0.5)

    s2 = await rest.get_state("automation.goodnight_routine")
    assert s2["attributes"].get("current", 0) > count_before
