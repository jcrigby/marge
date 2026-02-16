"""
CTS -- Automation API Tests

Tests automation listing, individual info, YAML read/write,
force trigger, enable/disable, toggle, and edge cases through
the REST and WebSocket APIs.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Listing ────────────────────────────────────

async def test_automation_list_returns_list(rest):
    """GET /api/automations returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6  # 6 loaded automations


@pytest.mark.parametrize("field", [
    "id", "alias", "enabled", "mode",
    "trigger_count", "condition_count", "action_count",
    "description",
])
async def test_automation_list_has_field(rest, field):
    """Automation config entries include expected field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert field in auto, f"Missing field: {field}"


async def test_automation_list_has_id_and_alias(rest):
    """Automation entries have non-empty alias."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "id" in auto
    assert "alias" in auto
    assert len(auto["alias"]) > 0


async def test_automation_list_has_counts(rest):
    """Automation entries include trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert auto["trigger_count"] >= 1
    assert auto["action_count"] >= 1


async def test_automation_list_has_mode(rest):
    """Automation entries include mode field with valid value."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert auto["mode"] in ["single", "parallel", "queued", "restart"]


# ── Automation YAML Read ──────────────────────────────────

async def test_automation_yaml_read(rest):
    """GET /api/config/automation/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    # Should contain YAML automation content
    assert "id:" in text or "alias:" in text


# ── Scene YAML Read ──────────────────────────────────────

async def test_scene_yaml_read(rest):
    """GET /api/config/scene/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    assert "id:" in text or "name:" in text


# ── Force Trigger ─────────────────────────────────────────

async def test_trigger_nonexistent_automation(rest):
    """Triggering nonexistent automation returns empty result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.does_not_exist"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Merged from depth: trigger via REST ──────────────────

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


# ── Merged from depth: trigger via WebSocket ─────────────

async def test_trigger_ws(ws):
    """WS call_service automation.trigger fires automation."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp.get("success", False) is True


# ── Merged from depth: enable/disable/toggle ─────────────

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


# -- merged from test_automation_trigger_depth.py --

async def test_automation_ids_unique(rest):
    """All automation IDs are unique."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [a["id"] for a in data]
    assert len(ids) == len(set(ids))


async def test_trigger_without_prefix(rest):
    """Trigger without 'automation.' prefix also works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "morning_wakeup"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_trigger_empty_entity_id(rest):
    """Trigger with empty entity_id returns 200 (no-op)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
