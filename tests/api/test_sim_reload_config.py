"""
CTS -- Sim Time, Reload, Check Config, Scene Config, Error Log Tests

Tests POST /api/sim/time, POST /api/config/core/reload,
POST /api/config/core/check_config, GET /api/config/scene/config,
GET /api/config/scene/yaml, PUT /api/config/scene/yaml,
and GET /api/error_log endpoints.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_sim_time_reflected_in_health(rest):
    """sim/time values appear in health endpoint."""
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "08:00:00", "chapter": "morning", "speed": 5},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["sim_time"] == "08:00:00"
    assert data["sim_chapter"] == "morning"
    assert data["sim_speed"] == 5


async def test_reload_automations_alt_path(rest):
    """POST /api/config/automation/reload returns success."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_scene_config_list(rest):
    """GET /api/config/scene/config returns scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # evening, goodnight


async def test_scene_yaml_get(rest):
    """GET /api/config/scene/yaml returns YAML string."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    assert "scene" in text.lower() or "evening" in text.lower() or "-" in text


async def test_automation_config_list(rest):
    """GET /api/config/automation/config returns automation list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6


async def test_automation_yaml_get(rest):
    """GET /api/config/automation/yaml returns YAML string."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    text = resp.text
    assert "trigger" in text.lower() or "alias" in text.lower() or "-" in text
