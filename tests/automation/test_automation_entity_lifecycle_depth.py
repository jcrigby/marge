"""
CTS -- Automation Entity Lifecycle Depth Tests

Tests automation entity states in the state machine: enabled/disabled
status reflected in entity state, trigger/turn_off/turn_on services
via REST, and automation toggle behavior.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Entity States ─────────────────────────────

async def test_automations_have_entities(rest):
    """Loaded automations have corresponding entities in state machine."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 1


async def test_enabled_automation_state_on(rest):
    """Enabled automation entity has state 'on'."""
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    # At least one should be on (enabled by default)
    on_count = sum(1 for s in auto_entities if s["state"] == "on")
    assert on_count >= 1


async def test_automation_turn_off_changes_state(rest):
    """automation.turn_off changes entity state to off."""
    # Get first automation entity
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.") and s["state"] == "on"
    )

    await rest.call_service("automation", "turn_off", {"entity_id": auto_eid})
    state = await rest.get_state(auto_eid)
    assert state["state"] == "off"

    # Re-enable for other tests
    await rest.call_service("automation", "turn_on", {"entity_id": auto_eid})


async def test_automation_turn_on_changes_state(rest):
    """automation.turn_on changes entity state to on."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.")
    )

    await rest.call_service("automation", "turn_off", {"entity_id": auto_eid})
    await rest.call_service("automation", "turn_on", {"entity_id": auto_eid})
    state = await rest.get_state(auto_eid)
    assert state["state"] == "on"


async def test_automation_toggle(rest):
    """automation.toggle flips entity state."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.") and s["state"] == "on"
    )

    await rest.call_service("automation", "toggle", {"entity_id": auto_eid})
    state = await rest.get_state(auto_eid)
    assert state["state"] == "off"

    # Toggle back
    await rest.call_service("automation", "toggle", {"entity_id": auto_eid})
    state = await rest.get_state(auto_eid)
    assert state["state"] == "on"


# ── Automation Trigger Service ───────────────────────────

async def test_automation_trigger_returns_200(rest):
    """automation.trigger service call returns 200."""
    states = await rest.get_states()
    auto_eid = next(
        s["entity_id"] for s in states
        if s["entity_id"].startswith("automation.")
    )

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        headers=rest._headers(),
        json={"entity_id": auto_eid},
    )
    assert resp.status_code == 200


# ── Automation Info Endpoint ─────────────────────────────

async def test_automation_list_returns_array(rest):
    """GET /api/config/automation/config returns array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_automation_list_nonempty(rest):
    """Automation list has entries (demo automations loaded)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert len(resp.json()) >= 1


async def test_automation_entry_has_alias(rest):
    """Automation entry has alias field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "alias" in entry


async def test_automation_entry_has_id(rest):
    """Automation entry has id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "id" in entry
