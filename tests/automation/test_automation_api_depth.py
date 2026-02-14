"""
CTS -- Automation API Depth Tests

Tests automation trigger/enable/disable via REST and WS,
automation config listing, trigger counting, and lifecycle.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_trigger_automation_rest(rest):
    """POST /api/services/automation/trigger fires automation."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.smoke_co_emergency"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_trigger_increments_count(rest):
    """Triggering automation increments current count."""
    state1 = await rest.get_state("automation.smoke_co_emergency")
    count1 = int(state1["attributes"].get("current", 0))

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.smoke_co_emergency"},
        headers=rest._headers(),
    )

    state2 = await rest.get_state("automation.smoke_co_emergency")
    count2 = int(state2["attributes"].get("current", 0))
    assert count2 > count1


async def test_automation_has_last_triggered(rest):
    """Triggered automation has last_triggered attribute."""
    await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.smoke_co_emergency"},
        headers=rest._headers(),
    )

    state = await rest.get_state("automation.smoke_co_emergency")
    lt = state["attributes"].get("last_triggered", "")
    assert len(lt) > 0
    assert "T" in lt


async def test_automation_config_has_fields(rest):
    """Automation config entries have expected fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "id" in auto
        assert "alias" in auto
        assert "enabled" in auto
        break


async def test_automation_config_has_counts(rest):
    """Automation config includes trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "trigger_count" in auto
        assert "condition_count" in auto
        assert "action_count" in auto
        break


async def test_automation_mode_field(rest):
    """Automation config includes mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "mode" in auto
        assert auto["mode"] in ["single", "parallel", "queued", "restart"]
        break


async def test_trigger_ws(ws):
    """WS call_service automation.trigger fires automation."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp.get("success", False) is True


async def test_automation_turn_off_on_cycle(rest):
    """Automation can be turned off and back on."""
    eid = "automation.smoke_co_emergency"

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state_off = await rest.get_state(eid)
    assert state_off["state"] == "off"

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state_on = await rest.get_state(eid)
    assert state_on["state"] == "on"


async def test_automation_toggle(rest):
    """automation.toggle flips state."""
    eid = "automation.smoke_co_emergency"

    state1 = await rest.get_state(eid)
    original = state1["state"]

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state2 = await rest.get_state(eid)
    assert state2["state"] != original

    # Toggle back
    await rest.client.post(
        f"{rest.base_url}/api/services/automation/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state3 = await rest.get_state(eid)
    assert state3["state"] == original


async def test_force_trigger_bypasses_disabled(rest):
    """Force trigger fires even when automation is off."""
    eid = "automation.smoke_co_emergency"

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state1 = await rest.get_state(eid)
    count1 = int(state1["attributes"].get("current", 0))

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state2 = await rest.get_state(eid)
    count2 = int(state2["attributes"].get("current", 0))
    assert count2 > count1

    await rest.client.post(
        f"{rest.base_url}/api/services/automation/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )


async def test_automation_description_field(rest):
    """Automation config includes description field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "description" in auto
        break
