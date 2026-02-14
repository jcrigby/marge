"""
CTS -- Automation Config Detail Depth Tests

Tests the automation config API endpoints: list automations with metadata,
get/put automation YAML, reload automations, and automation info fields.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── List Automations Config ───────────────────────────────

async def test_list_automations_returns_list(rest):
    """GET /api/config/automation/config returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_automation_has_id_and_alias(rest):
    """Each automation has id and alias fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for auto in resp.json():
        assert "id" in auto
        assert "alias" in auto


async def test_automation_has_metadata(rest):
    """Each automation has trigger_count, condition_count, action_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    auto = resp.json()[0]
    assert "trigger_count" in auto
    assert "condition_count" in auto
    assert "action_count" in auto


async def test_automation_has_enabled(rest):
    """Each automation has enabled field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    for auto in resp.json():
        assert "enabled" in auto
        assert isinstance(auto["enabled"], bool)


async def test_automation_has_mode(rest):
    """Each automation has mode field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    auto = resp.json()[0]
    assert "mode" in auto


async def test_automation_morning_wakeup_exists(rest):
    """Known automation morning_wakeup appears in config list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    ids = [a["id"] for a in resp.json()]
    assert "morning_wakeup" in ids


# ── Automation YAML ───────────────────────────────────────

async def test_get_automation_yaml(rest):
    """GET /api/config/automation/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "text/yaml" in resp.headers.get("content-type", "")
    assert "trigger" in resp.text or "alias" in resp.text


async def test_automation_yaml_has_content(rest):
    """Automation YAML is non-empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert len(resp.text) > 50


# ── Reload Automations ───────────────────────────────────

async def test_reload_automations(rest):
    """POST /api/config/core/reload returns ok with count."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
    assert "automations_reloaded" in data
    assert data["automations_reloaded"] > 0


async def test_reload_automation_route(rest):
    """POST /api/config/automation/reload also works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


# ── Scene Config ──────────────────────────────────────────

async def test_list_scenes_config(rest):
    """GET /api/config/scene/config returns scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_get_scene_yaml(rest):
    """GET /api/config/scene/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "text/yaml" in resp.headers.get("content-type", "")
