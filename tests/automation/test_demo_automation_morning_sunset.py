"""
CTS -- Demo Automation: Morning Wake-Up and Sunset End-to-End

Tests morning_wakeup (time trigger, force-trigger via service) and
sunset_lights (sun trigger, scene activation) automations.
Verifies multi-entity action targets and attribute passthrough.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Morning Wake-Up ────────────────────────────────────────

async def _setup_morning(rest):
    """Baseline for morning_wakeup tests."""
    await rest.set_state("light.bedroom", "off", {"brightness": 0})
    await rest.set_state("climate.thermostat", "heat", {"temperature": 66})
    await rest.set_state("switch.coffee_maker", "off")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.1)


@pytest.mark.marge_only
async def test_morning_force_trigger_turns_on_bedroom(rest):
    """Force-trigger morning_wakeup turns on bedroom light."""
    await _setup_morning(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.bedroom")
    assert state["state"] == "on"


@pytest.mark.marge_only
async def test_morning_force_trigger_sets_brightness_51(rest):
    """Force-trigger morning_wakeup sets bedroom brightness to 51."""
    await _setup_morning(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.bedroom")
    assert state["attributes"].get("brightness") == 51


@pytest.mark.marge_only
async def test_morning_force_trigger_sets_color_temp(rest):
    """Force-trigger morning_wakeup sets bedroom color_temp to 400."""
    await _setup_morning(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.bedroom")
    assert state["attributes"].get("color_temp") == 400


@pytest.mark.marge_only
async def test_morning_force_trigger_sets_thermostat_70(rest):
    """Force-trigger morning_wakeup sets thermostat to 70."""
    await _setup_morning(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("climate.thermostat")
    assert state["attributes"].get("temperature") == 70


@pytest.mark.marge_only
async def test_morning_force_trigger_turns_on_coffee(rest):
    """Force-trigger morning_wakeup turns on coffee maker."""
    await _setup_morning(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.morning_wake_up"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("switch.coffee_maker")
    assert state["state"] == "on"


async def test_morning_entity_state_on(rest):
    """morning_wakeup automation entity is 'on' when enabled."""
    state = await rest.get_state("automation.morning_wake_up")
    assert state is not None
    assert state["state"] == "on"


@pytest.mark.marge_only
async def test_morning_has_time_trigger(rest):
    """morning_wakeup has exactly 1 trigger."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    morning = next(a for a in data if a["id"] == "morning_wake_up")
    assert morning["trigger_count"] == 1


@pytest.mark.marge_only
async def test_morning_has_3_actions(rest):
    """morning_wakeup has 3 actions (light, climate, switch)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    morning = next(a for a in data if a["id"] == "morning_wake_up")
    assert morning["action_count"] == 3


# ── Sunset Lights ──────────────────────────────────────────

async def _setup_sunset(rest):
    """Baseline for sunset_lights tests."""
    await rest.set_state("light.porch", "off")
    await rest.set_state("light.pathway", "off")
    await rest.set_state("light.living_room_main", "off")
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.1)


@pytest.mark.marge_only
async def test_sunset_force_trigger_turns_on_porch(rest):
    """Force-trigger sunset turns on porch light."""
    await _setup_sunset(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.porch")
    assert state["state"] == "on"


@pytest.mark.marge_only
async def test_sunset_force_trigger_turns_on_pathway(rest):
    """Force-trigger sunset turns on pathway light."""
    await _setup_sunset(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.5)
    state = await rest.get_state("light.pathway")
    assert state["state"] == "on"


@pytest.mark.marge_only
async def test_sunset_force_trigger_activates_evening_scene(rest):
    """Force-trigger sunset activates evening scene (living room on)."""
    await _setup_sunset(rest)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.sunset_exterior_and_evening_scene"
    })
    await asyncio.sleep(0.5)
    # Evening scene turns on living room main
    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


@pytest.mark.marge_only
async def test_sunset_has_sun_trigger(rest):
    """sunset_lights has 1 trigger (sun event)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    sunset = next(a for a in data if a["id"] == "sunset_exterior_and_evening_scene")
    assert sunset["trigger_count"] == 1


@pytest.mark.marge_only
async def test_sunset_has_2_actions(rest):
    """sunset_lights has 2 actions (lights + scene)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    sunset = next(a for a in data if a["id"] == "sunset_exterior_and_evening_scene")
    assert sunset["action_count"] == 2
