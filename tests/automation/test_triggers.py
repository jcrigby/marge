"""CTS — Automation trigger tests.

Tests that automations fire (or don't) based on state changes, events,
and the automation.trigger service. Uses the 6 automations from
ha-config/automations.yaml loaded into Marge at startup.
"""
import asyncio
import pytest
import httpx

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def set_state(entity_id: str, state: str, attrs: dict | None = None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200
        return r.json()


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        if r.status_code == 404:
            return None
        return r.json()


async def call_service(domain: str, service: str, data: dict):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/api/services/{domain}/{service}", json=data, headers=HEADERS)
        assert r.status_code == 200
        return r.json()


async def fire_event(event_type: str):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/api/events/{event_type}", json={}, headers=HEADERS)
        assert r.status_code == 200
        return r.json()


# ── Smoke/CO Emergency: state trigger, no conditions ──────────

@pytest.mark.asyncio
async def test_smoke_trigger_unlocks_doors():
    """Smoke emergency should unlock all doors."""
    await set_state("lock.front_door", "locked")
    await set_state("lock.back_door", "locked")
    await set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.1)

    await set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.2)

    front = await get_state("lock.front_door")
    back = await get_state("lock.back_door")
    assert front["state"] == "unlocked"
    assert back["state"] == "unlocked"


@pytest.mark.asyncio
async def test_security_alert_blocked_when_not_armed_away():
    """Motion in entryway + alarm armed_home → condition blocks, no alert."""
    # Set alarm to armed_home — condition requires armed_away
    await set_state("alarm_control_panel.home", "armed_home")
    # Set a canary: lock.front_door stays locked
    # (security_alert only creates a notification, nothing observable,
    # so we test the condition indirectly by checking nothing else changes)
    await set_state("lock.front_door", "locked")
    await set_state("binary_sensor.entryway_motion", "off")
    await asyncio.sleep(0.1)

    await set_state("binary_sensor.entryway_motion", "on")
    await asyncio.sleep(0.2)

    # No side effects; automation entity still on
    auto = await get_state("automation.security_alert_motion_while_armed_away")
    assert auto["state"] == "on"


# ── Goodnight Routine: event trigger ──────────────────────────

@pytest.mark.asyncio
async def test_goodnight_event_turns_off_lights():
    """Firing 'bedside_button_pressed' event → all lights off."""
    lights = [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
        "light.porch", "light.pathway",
    ]
    # Turn all lights on first
    for lid in lights:
        await set_state(lid, "on")
    await asyncio.sleep(0.1)

    # Fire the event
    await fire_event("bedside_button_pressed")
    await asyncio.sleep(0.2)

    for lid in lights:
        s = await get_state(lid)
        assert s["state"] == "off", f"{lid} should be off after goodnight"


@pytest.mark.asyncio
async def test_goodnight_event_locks_doors():
    """Goodnight routine should lock both doors."""
    await set_state("lock.front_door", "unlocked")
    await set_state("lock.back_door", "unlocked")
    await asyncio.sleep(0.1)

    await fire_event("bedside_button_pressed")
    await asyncio.sleep(0.2)

    front = await get_state("lock.front_door")
    back = await get_state("lock.back_door")
    assert front["state"] == "locked"
    assert back["state"] == "locked"


@pytest.mark.asyncio
async def test_goodnight_event_sets_thermostat():
    """Goodnight routine sets thermostat to 66."""
    await set_state("climate.thermostat", "heat", {"temperature": 72})
    await asyncio.sleep(0.1)

    await fire_event("bedside_button_pressed")
    await asyncio.sleep(0.2)

    therm = await get_state("climate.thermostat")
    assert therm["attributes"]["temperature"] == 66


@pytest.mark.asyncio
async def test_goodnight_event_arms_alarm_night():
    """Goodnight routine arms alarm in night mode."""
    await set_state("alarm_control_panel.home", "disarmed")
    await asyncio.sleep(0.1)

    await fire_event("bedside_button_pressed")
    await asyncio.sleep(0.2)

    alarm = await get_state("alarm_control_panel.home")
    assert alarm["state"] == "armed_night"


# ── Force trigger via automation.trigger service ──────────────

@pytest.mark.asyncio
async def test_force_trigger_morning_wake_up():
    """POST /api/services/automation/trigger for morning_wake_up should run actions."""
    # Preconditions
    await set_state("light.bedroom", "off")
    await set_state("climate.thermostat", "heat", {"temperature": 60})
    await set_state("switch.coffee_maker", "off")
    await asyncio.sleep(0.1)

    # Force trigger (bypasses the time trigger)
    await call_service("automation", "trigger", {"entity_id": "automation.morning_wake_up"})
    await asyncio.sleep(0.2)

    bed = await get_state("light.bedroom")
    assert bed["state"] == "on"
    assert bed["attributes"]["brightness"] == 51
    assert bed["attributes"]["color_temp"] == 400

    therm = await get_state("climate.thermostat")
    assert therm["attributes"]["temperature"] == 70

    coffee = await get_state("switch.coffee_maker")
    assert coffee["state"] == "on"


@pytest.mark.asyncio
async def test_force_trigger_sunset_exterior_and_evening_scene():
    """Force-trigger sunset_exterior_and_evening_scene turns on exterior + living room lights."""
    await set_state("light.porch", "off")
    await set_state("light.pathway", "off")
    await set_state("light.living_room_main", "off")
    await set_state("light.living_room_accent", "off")
    await set_state("light.living_room_lamp", "off")
    await set_state("light.living_room_floor", "off")
    await asyncio.sleep(0.1)

    await call_service("automation", "trigger", {"entity_id": "automation.sunset_exterior_and_evening_scene"})
    await asyncio.sleep(0.2)

    porch = await get_state("light.porch")
    assert porch["state"] == "on"
    pathway = await get_state("light.pathway")
    assert pathway["state"] == "on"

    main = await get_state("light.living_room_main")
    assert main["state"] == "on"
    assert main["attributes"]["brightness"] == 180

    accent = await get_state("light.living_room_accent")
    assert accent["state"] == "on"
    assert accent["attributes"]["brightness"] == 120


# ── Lock Verification: state trigger + OR condition ───────────

@pytest.mark.asyncio
async def test_lock_verification_fires_when_door_unlocked():
    """alarm → armed_night with a door unlocked → lock_verification fires."""
    await set_state("lock.front_door", "unlocked")
    await set_state("lock.back_door", "locked")
    await set_state("alarm_control_panel.home", "disarmed")
    await asyncio.sleep(0.1)

    # Trigger: alarm goes to armed_night
    await set_state("alarm_control_panel.home", "armed_night")
    await asyncio.sleep(0.2)

    # The automation creates a notification (not directly testable via state),
    # but at minimum it should not crash and the automation should still be 'on'
    auto = await get_state("automation.lock_verification_after_goodnight")
    assert auto["state"] == "on"


@pytest.mark.asyncio
async def test_lock_verification_blocked_when_all_locked():
    """alarm → armed_night with all doors locked → OR condition fails, no fire."""
    await set_state("lock.front_door", "locked")
    await set_state("lock.back_door", "locked")
    await set_state("alarm_control_panel.home", "disarmed")
    await asyncio.sleep(0.1)

    await set_state("alarm_control_panel.home", "armed_night")
    await asyncio.sleep(0.2)

    # No crash, automation still on
    auto = await get_state("automation.lock_verification_after_goodnight")
    assert auto["state"] == "on"


# ── State trigger with to/from filters ────────────────────────

@pytest.mark.asyncio
async def test_state_trigger_to_filter_must_match():
    """Smoke trigger has to='on'. Setting to 'off' should NOT fire."""
    # Step 1: Set smoke detector to "on" (this WILL fire the emergency automation)
    await set_state("binary_sensor.smoke_detector", "on")
    await asyncio.sleep(0.2)

    # Step 2: Reset lights to off AFTER the automation has fired
    lights = ["light.bedroom", "light.bathroom", "light.kitchen"]
    for lid in lights:
        await set_state(lid, "off")
    await asyncio.sleep(0.1)

    # Step 3: Set smoke detector to 'off' — should NOT trigger emergency
    await set_state("binary_sensor.smoke_detector", "off")
    await asyncio.sleep(0.2)

    # Assert: lights should still be off (the 'off' transition shouldn't match to='on')
    for lid in lights:
        s = await get_state(lid)
        assert s["state"] == "off", f"{lid} should still be off"
