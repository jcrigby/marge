"""
CTS -- REST Automation & Scene Config Depth Tests

Tests GET /api/config/automation/config, /api/config/scene/config,
automation YAML endpoint, scene YAML endpoint, and reload endpoint.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Config ───────────────────────────────────

async def test_automation_config_returns_200(rest):
    """GET /api/config/automation/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_automation_config_returns_array(rest):
    """Automation config returns list of automations."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_automation_config_entries_have_id(rest):
    """Each automation config entry has id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        assert "id" in data[0]


async def test_automation_config_entries_have_alias(rest):
    """Each automation config entry has alias field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        assert "alias" in data[0]


# ── Automation YAML ─────────────────────────────────────

async def test_automation_yaml_returns_200(rest):
    """GET /api/config/automation/yaml returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_automation_yaml_returns_text(rest):
    """Automation YAML endpoint returns text content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert len(resp.text) > 0


# ── Scene Config ────────────────────────────────────────

async def test_scene_config_returns_200(rest):
    """GET /api/config/scene/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_scene_config_returns_array(rest):
    """Scene config returns list of scenes."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


# ── Scene YAML ──────────────────────────────────────────

async def test_scene_yaml_returns_200(rest):
    """GET /api/config/scene/yaml returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Reload ──────────────────────────────────────────────

async def test_reload_automations_returns_200(rest):
    """POST /api/config/core/reload returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_automation_reload_endpoint(rest):
    """POST /api/config/automation/reload returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
