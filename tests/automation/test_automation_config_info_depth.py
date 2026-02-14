"""
CTS -- Automation Config Info Depth Tests

Tests GET /api/config/automation/config: field presence for each
automation entry, enabled state, metadata accuracy, and consistency
with automation entity states.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Listing ───────────────────────────────────────────────

async def test_automation_list_returns_array(rest):
    """GET /api/config/automation/config returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_automation_list_nonempty(rest):
    """Automation list has at least one entry (demo automations loaded)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1


# ── Entry Fields ──────────────────────────────────────────

async def test_automation_entry_has_id(rest):
    """Each automation entry has id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "id" in entry
        assert len(entry["id"]) > 0


async def test_automation_entry_has_alias(rest):
    """Each automation entry has alias field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "alias" in entry


async def test_automation_entry_has_description(rest):
    """Each automation entry has description field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "description" in entry


async def test_automation_entry_has_mode(rest):
    """Each automation entry has mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "mode" in entry
        assert entry["mode"] in ("single", "queued", "restart", "parallel")


async def test_automation_entry_has_enabled(rest):
    """Each automation entry has enabled field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "enabled" in entry
        assert isinstance(entry["enabled"], bool)


async def test_automation_entry_has_trigger_count(rest):
    """Each automation entry has trigger_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "trigger_count" in entry
        assert isinstance(entry["trigger_count"], int)


async def test_automation_entry_has_condition_count(rest):
    """Each automation entry has condition_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "condition_count" in entry
        assert isinstance(entry["condition_count"], int)


async def test_automation_entry_has_action_count(rest):
    """Each automation entry has action_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "action_count" in entry
        assert isinstance(entry["action_count"], int)
        assert entry["action_count"] >= 1


async def test_automation_entry_has_total_triggers(rest):
    """Each automation entry has total_triggers counter."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "total_triggers" in entry
        assert isinstance(entry["total_triggers"], int)


async def test_automation_entry_has_last_triggered(rest):
    """Each automation entry has last_triggered field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "last_triggered" in entry


# ── Consistency with Entity States ────────────────────────

async def test_automations_have_entity_states(rest):
    """Each automation has a corresponding automation.* entity."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    states = await rest.get_states()
    automation_eids = {s["entity_id"] for s in states if s["entity_id"].startswith("automation.")}

    for auto in automations:
        eid = f"automation.{auto['id']}"
        assert eid in automation_eids, f"Missing entity for automation {auto['id']}"


async def test_enabled_automation_entity_on(rest):
    """Enabled automation has entity state 'on'."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    automations = resp.json()
    enabled = [a for a in automations if a["enabled"]]
    assert len(enabled) >= 1  # At least one enabled

    for auto in enabled:
        eid = f"automation.{auto['id']}"
        state = await rest.get_state(eid)
        assert state["state"] == "on"
