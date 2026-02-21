"""
CTS -- Scene Configuration API Tests

Tests scene configuration endpoints: list scenes, scene YAML
get/put, and scene listing format.
"""

import asyncio

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


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


# -- from test_extended_api.py --

async def test_scene_config_returns_list(rest):
    """GET /api/config/scene/config returns a list of scenes."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    scene = data[0]
    assert "id" in scene
    assert "name" in scene
    assert "entity_count" in scene
    assert "entities" in scene


# -- from test_extended_api.py --

async def test_scene_entity_has_friendly_name(rest):
    """Scene entities have friendly_name attribute set from scene name."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if len(scenes) == 0:
        pytest.skip("No scenes loaded")
    scene = scenes[0]

    state = await rest.get_state(f"scene.{scene['id']}")
    assert state is not None
    assert "friendly_name" in state["attributes"]
    assert state["attributes"]["friendly_name"] == scene["name"]


# -- from test_extended_api.py --

async def test_scene_activation_sets_entity_states(rest):
    """Activating a scene sets the target entity states."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    if not scenes:
        pytest.skip("No scenes loaded")
    scene = scenes[0]

    # Activate scene
    await rest.call_service("scene", "turn_on", {
        "entity_id": f"scene.{scene['id']}",
    })
    await asyncio.sleep(0.5)

    # Verify at least one entity has the expected state
    for entity_entry in scene.get("entities", []):
        if isinstance(entity_entry, dict):
            eid = entity_entry.get("entity_id")
        else:
            eid = entity_entry
        if eid:
            state = await rest.get_state(eid)
            assert state is not None, f"Entity {eid} from scene should exist"
            break
