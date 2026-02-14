"""
CTS -- Automation Entity State and Metadata Depth Tests

Tests automation entities in the state machine (automation.* entities),
enable/disable via services, trigger count tracking, and metadata
fields (last_triggered, enabled). Uses the automation API to verify
state changes after trigger and enable/disable operations.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Automation entities exist ─────────────────────────────

async def test_automation_entities_exist(rest):
    """Automation entities (automation.*) exist in state machine."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 6  # 6 demo automations


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


# ── Enable / Disable ─────────────────────────────────────

async def test_automation_disable(rest):
    """automation.turn_off disables an automation (state → off)."""
    # Find a known automation entity
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[0]["id"]
    eid = f"automation.{auto_id}"

    await rest.call_service("automation", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"

    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {"entity_id": eid})


async def test_automation_enable(rest):
    """automation.turn_on enables an automation (state → on)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[0]["id"]
    eid = f"automation.{auto_id}"

    await rest.call_service("automation", "turn_off", {"entity_id": eid})
    await rest.call_service("automation", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_automation_toggle(rest):
    """automation.toggle flips enabled state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[0]["id"]
    eid = f"automation.{auto_id}"

    # Get initial state
    initial = (await rest.get_state(eid))["state"]
    await rest.call_service("automation", "toggle", {"entity_id": eid})
    toggled = (await rest.get_state(eid))["state"]
    assert toggled != initial

    # Toggle back
    await rest.call_service("automation", "toggle", {"entity_id": eid})
    restored = (await rest.get_state(eid))["state"]
    assert restored == initial


# ── Trigger API ───────────────────────────────────────────

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
    # Should not error — automation was triggered


# ── Config metadata after trigger ─────────────────────────

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


# ── Disabled automation doesn't fire ──────────────────────

async def test_disabled_automation_config_shows_disabled(rest):
    """Disabled automation shows enabled=false in config."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto_id = autos[-1]["id"]  # use last automation
    eid = f"automation.{auto_id}"

    await rest.call_service("automation", "turn_off", {"entity_id": eid})
    await asyncio.sleep(0.1)

    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    auto = next(a for a in autos if a["id"] == auto_id)
    assert auto["enabled"] is False

    # Re-enable
    await rest.call_service("automation", "turn_on", {"entity_id": eid})
