"""
CTS -- Configuration and YAML Management Tests

Tests the automation configuration API: listing, updating, saving,
and reloading automations via REST API.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── List Automations ─────────────────────────────────────

async def test_list_automations_returns_list(rest):
    """GET /api/config/automation/config returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_list_automations_has_id(rest):
    """Each automation entry has an id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "id" in auto


async def test_list_automations_has_alias(rest):
    """Each automation entry has an alias field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "alias" in auto


async def test_list_automations_has_counts(rest):
    """Each automation entry has trigger/condition/action counts."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "trigger_count" in auto
    assert "action_count" in auto
    assert auto["trigger_count"] >= 1
    assert auto["action_count"] >= 1


# ── Reload Automations ───────────────────────────────────

async def test_reload_automations(rest):
    """POST /api/config/core/reload reloads automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "automations_reloaded" in data
    assert data["automations_reloaded"] >= 1


async def test_reload_preserves_entities(rest):
    """Reload does not remove automation entities."""
    # Get automations before
    states_before = await rest.get_states()
    auto_before = [s for s in states_before if s["entity_id"].startswith("automation.")]

    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Get automations after
    states_after = await rest.get_states()
    auto_after = [s for s in states_after if s["entity_id"].startswith("automation.")]

    assert len(auto_after) >= len(auto_before)


# ── Check Config ─────────────────────────────────────────

async def test_check_config_valid(rest):
    """POST /api/config/core/check_config returns valid result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert data["result"] in ["valid", "invalid"]


# ── Error Log ────────────────────────────────────────────

async def test_error_log_endpoint(rest):
    """GET /api/error_log returns text content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.text, str)


# ── Config Endpoint ──────────────────────────────────────

async def test_config_has_version(rest):
    """GET /api/config has version field."""
    data = await rest.get_config()
    assert "version" in data
    assert isinstance(data["version"], str)


async def test_config_has_location_name(rest):
    """GET /api/config has location_name."""
    data = await rest.get_config()
    assert "location_name" in data
    assert len(data["location_name"]) > 0


async def test_config_has_elevation(rest):
    """GET /api/config has elevation."""
    data = await rest.get_config()
    assert "elevation" in data
    assert isinstance(data["elevation"], (int, float))


# -- from test_extended_api.py --

async def test_automation_config_returns_list(rest):
    """GET /api/config/automation/config returns a list of automations."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Each entry should have id, alias, and trigger info
    auto = data[0]
    assert "id" in auto
    assert "alias" in auto
    assert "trigger_count" in auto
    assert "action_count" in auto
    assert "enabled" in auto


# -- from test_extended_api.py --

async def test_automation_config_has_metadata(rest):
    """Automation config includes runtime metadata fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    auto = data[0]
    assert "total_triggers" in auto
    assert isinstance(auto["total_triggers"], int)
    assert "last_triggered" in auto
    assert "mode" in auto


# -- from test_extended_api.py --

async def test_automation_entity_has_friendly_name(rest):
    """Automation entities have friendly_name attribute set from alias."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if len(automations) == 0:
        pytest.skip("No automations loaded")
    auto = automations[0]

    state = await rest.get_state(f"automation.{auto['id']}")
    assert state is not None
    assert "friendly_name" in state["attributes"]
    assert state["attributes"]["friendly_name"] == auto["alias"]


# -- from test_extended_api.py --

async def test_automation_trigger_updates_metadata(rest):
    """Triggering an automation updates last_triggered and current count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    if len(automations) == 0:
        pytest.skip("No automations loaded")
    auto = automations[0]
    initial_count = auto["total_triggers"]

    # Trigger the automation
    await rest.call_service("automation", "trigger", {"entity_id": f"automation.{auto['id']}"})
    await asyncio.sleep(0.5)

    # Check metadata was updated
    resp2 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    updated = next(a for a in resp2.json() if a["id"] == auto["id"])
    assert updated["total_triggers"] == initial_count + 1
    assert updated["last_triggered"] is not None


# -- from test_extended_api.py --

async def test_automation_trigger_via_service(rest):
    """POST /api/services/automation/trigger fires an automation."""
    # Get first automation ID
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if not autos:
        pytest.skip("No automations loaded")
    auto_id = autos[0]["id"]
    initial_count = autos[0]["total_triggers"]

    # Trigger
    await rest.call_service("automation", "trigger", {"entity_id": f"automation.{auto_id}"})

    # Verify count increased
    await asyncio.sleep(0.5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    updated = resp.json()
    auto = next(a for a in updated if a["id"] == auto_id)
    assert auto["total_triggers"] >= initial_count + 1
