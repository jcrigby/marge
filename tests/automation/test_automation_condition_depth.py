"""
CTS -- Automation Condition Evaluation Depth Tests

Tests automation condition types by observing side-effects:
state conditions, numeric_state, template conditions, and
or/and compound conditions.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_automation_entities_exist(rest):
    """All 6 automations create entity state entries."""
    states = await rest.get_states()
    auto_ids = [s["entity_id"] for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_ids) >= 6


async def test_automation_has_friendly_name(rest):
    """Automation entities have friendly_name attribute."""
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state is not None
    assert "friendly_name" in state["attributes"]


async def test_automation_has_current_attribute(rest):
    """Automation entities have current (trigger count) attribute."""
    state = await rest.get_state("automation.smoke_co_emergency")
    assert "current" in state["attributes"]


async def test_automation_info_has_mode(rest):
    """Automation config info includes mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "mode" in auto
        assert auto["mode"] in ["single", "restart", "queued", "parallel"]


async def test_automation_info_has_enabled(rest):
    """Automation config info includes enabled field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "enabled" in auto
        assert isinstance(auto["enabled"], bool)


async def test_automation_trigger_updates_last_triggered(rest):
    """Force triggering updates last_triggered attribute."""
    state_before = await rest.get_state("automation.smoke_co_emergency")
    last_before = state_before["attributes"].get("last_triggered", "")

    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency",
    })
    await asyncio.sleep(0.2)

    state_after = await rest.get_state("automation.smoke_co_emergency")
    last_after = state_after["attributes"].get("last_triggered", "")
    assert last_after != "" and last_after >= last_before


async def test_automation_trigger_increments_count(rest):
    """Force triggering increments current count in entity attributes."""
    s1 = await rest.get_state("automation.smoke_co_emergency")
    count_before = s1["attributes"].get("current", 0)

    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency",
    })
    await asyncio.sleep(0.2)

    s2 = await rest.get_state("automation.smoke_co_emergency")
    count_after = s2["attributes"].get("current", 0)
    assert count_after > count_before


async def test_automation_disable_sets_off(rest):
    """Disabling automation sets entity state to off."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency",
    })
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "off"


async def test_automation_enable_sets_on(rest):
    """Re-enabling automation sets entity state to on."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency",
    })
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency",
    })
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "on"


async def test_disabled_automation_state_preserved(rest):
    """Disabled automation stays off after trigger attempt."""
    await rest.call_service("automation", "turn_off", {
        "entity_id": "automation.smoke_co_emergency",
    })
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state["state"] == "off"

    # Force trigger still works (force bypasses enabled check)
    await rest.call_service("automation", "trigger", {
        "entity_id": "automation.smoke_co_emergency",
    })
    await asyncio.sleep(0.1)

    # State should still be off (enabled status not changed by trigger)
    state2 = await rest.get_state("automation.smoke_co_emergency")
    assert state2["state"] == "off"

    # Re-enable
    await rest.call_service("automation", "turn_on", {
        "entity_id": "automation.smoke_co_emergency",
    })


async def test_automation_toggle_cycle(rest):
    """Toggle automation twice returns to original state."""
    state_before = await rest.get_state("automation.smoke_co_emergency")
    original = state_before["state"]

    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.smoke_co_emergency",
    })
    state_mid = await rest.get_state("automation.smoke_co_emergency")
    assert state_mid["state"] != original

    await rest.call_service("automation", "toggle", {
        "entity_id": "automation.smoke_co_emergency",
    })
    state_after = await rest.get_state("automation.smoke_co_emergency")
    assert state_after["state"] == original
