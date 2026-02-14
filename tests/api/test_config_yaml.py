"""
CTS -- Configuration and YAML Management Tests

Tests the automation configuration API: listing, updating, saving,
and reloading automations via REST API.
"""

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
