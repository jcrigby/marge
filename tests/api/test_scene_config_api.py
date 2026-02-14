"""
CTS -- Scene Configuration API Tests

Tests scene configuration endpoints: list scenes, scene YAML
get/put, and scene listing format.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_scenes_returns_list(rest):
    """GET /api/config/scene/config returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_list_scenes_has_id(rest):
    """Each scene entry has an id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "id" in scene


async def test_list_scenes_has_name(rest):
    """Each scene entry has a name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "name" in scene


async def test_list_scenes_has_entity_count(rest):
    """Each scene entry has entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "entity_count" in scene
        assert scene["entity_count"] >= 1


async def test_get_scene_yaml(rest):
    """GET /api/config/scene/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.text) > 0


async def test_scene_evening_in_list(rest):
    """Evening scene appears in the scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    names = [s["name"] for s in data]
    assert "Evening" in names


async def test_scene_goodnight_in_list(rest):
    """Goodnight scene appears in the scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    names = [s["name"] for s in data]
    assert "Goodnight" in names
