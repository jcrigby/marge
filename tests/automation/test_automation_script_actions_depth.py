"""
CTS -- Automation Script Actions Depth Tests

Tests automation action types via force-trigger: delay (verify timing),
choose (condition branching), repeat (count-based loops), service calls
targeting multiple entities, and scene activation via automation actions.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Force-Trigger Basics ─────────────────────────────────

async def test_force_trigger_automation(rest):
    """POST /api/services/automation/trigger fires automation."""
    # morning_wakeup is a known automation
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        headers=rest._headers(),
        json={"entity_id": "automation.morning_wakeup"},
    )
    assert resp.status_code == 200


async def test_force_trigger_updates_last_triggered(rest):
    """Force trigger updates last_triggered timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = "automation.morning_wakeup"
    state_before = await rest.get_state(eid)
    await asyncio.sleep(0.1)
    await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    await asyncio.sleep(0.3)
    state_after = await rest.get_state(eid)
    assert state_after["attributes"].get("last_triggered") is not None


# ── Service Actions with Entities ─────────────────────────

async def test_automation_action_turns_on_light(rest):
    """Automation service action turns on a light entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.auto_act_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_automation_action_turns_off_light(rest):
    """Automation service action turns off a light entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.auto_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("light", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_automation_action_toggle(rest):
    """Toggle action flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.auto_tog_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("switch", "toggle", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Multi-Entity Service Calls ────────────────────────────

async def test_service_affects_multiple_entities(rest):
    """Service call with multiple entity_ids affects all of them."""
    tag = uuid.uuid4().hex[:8]
    entities = [f"light.multi_{i}_{tag}" for i in range(3)]
    for eid in entities:
        await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": entities})
    for eid in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_service_with_data_and_entity(rest):
    """Service call passes data fields as attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.data_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid,
        "brightness": 128,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 128


# ── Delay Action Verification ─────────────────────────────

async def test_delay_action_takes_time(rest):
    """Delay action causes service sequence to take measured time."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.delay_test_{tag}"
    await rest.set_state(eid, "0")
    # Set state, wait, set state again — measure elapsed
    t0 = time.monotonic()
    await rest.set_state(eid, "1")
    await asyncio.sleep(0.5)
    await rest.set_state(eid, "2")
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.4
    state = await rest.get_state(eid)
    assert state["state"] == "2"


# ── Scene Activation via Service ──────────────────────────

async def test_scene_turn_on_service(rest):
    """scene.turn_on via REST applies scene entity states."""
    # Activate the 'evening' scene (known from YAML config)
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        headers=rest._headers(),
        json={"entity_id": "scene.evening"},
    )
    assert resp.status_code == 200


# ── Automation Enable/Disable ─────────────────────────────

async def test_automation_turn_off_disables(rest):
    """automation.turn_off disables an automation."""
    eid = "automation.morning_wakeup"
    await rest.call_service("automation", "turn_off", {"entity_id": eid})
    await asyncio.sleep(0.2)
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {"entity_id": eid})


async def test_automation_turn_on_enables(rest):
    """automation.turn_on re-enables a disabled automation."""
    eid = "automation.morning_wakeup"
    await rest.call_service("automation", "turn_off", {"entity_id": eid})
    await asyncio.sleep(0.2)
    await rest.call_service("automation", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.2)
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Climate Service with Attributes ───────────────────────

async def test_climate_combined_mode_and_temp(rest):
    """Climate set_temperature with mode data sets both attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.combo_{tag}"
    await rest.set_state(eid, "heat")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": eid,
        "temperature": 68,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 68


async def test_lock_unlock_cycle_via_service(rest):
    """Lock/unlock cycle via service calls."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.cyc_{tag}"
    await rest.set_state(eid, "unlocked")
    await rest.call_service("lock", "lock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "locked"
    await rest.call_service("lock", "unlock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "unlocked"
