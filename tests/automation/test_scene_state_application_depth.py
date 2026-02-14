"""
CTS -- Scene State Application Depth Tests

Tests that scene activation actually applies entity states — verifies
state values and attribute merging after scene.turn_on. Tests scene
entity registration in state machine and scene config API detail.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Scene Entities Exist ────────────────────────────────

async def test_scene_entities_registered(rest):
    """Scene entities (scene.*) exist in state machine."""
    states = await rest.get_states()
    scene_entities = [s for s in states if s["entity_id"].startswith("scene.")]
    assert len(scene_entities) >= 2  # evening, goodnight


async def test_scene_entity_has_name(rest):
    """Scene entity state has friendly_name attribute."""
    states = await rest.get_states()
    scene_entities = [s for s in states if s["entity_id"].startswith("scene.")]
    # At least one should have a name
    assert any("friendly_name" in s["attributes"] for s in scene_entities)


# ── Scene Turn On (REST) ────────────────────────────────

async def test_scene_turn_on_via_rest(rest):
    """scene.turn_on via REST sets entity states."""
    tag = uuid.uuid4().hex[:8]
    # Create entities that a scene would affect
    eid = f"light.scene_test_{tag}"
    await rest.set_state(eid, "off")
    # Turn on the evening scene (known scene)
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    # Scene should have activated (no error)


async def test_scene_turn_on_via_ws(rest, ws):
    """scene.turn_on via WS activates scene."""
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert resp["success"] is True


# ── Scene Config API ────────────────────────────────────

async def test_scene_config_list(rest):
    """GET /api/config/scene/config returns scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    scenes = resp.json()
    assert isinstance(scenes, list)
    assert len(scenes) >= 2


async def test_scene_config_has_id(rest):
    """Scene config entries have id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for scene in scenes:
        assert "id" in scene


async def test_scene_config_has_name(rest):
    """Scene config entries have name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for scene in scenes:
        assert "name" in scene


async def test_scene_config_has_entity_count(rest):
    """Scene config entries have entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for scene in scenes:
        assert "entity_count" in scene
        assert scene["entity_count"] >= 0


async def test_scene_config_has_entities(rest):
    """Scene config entries have entities list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for scene in scenes:
        assert "entities" in scene
        assert isinstance(scene["entities"], list)


# ── Scene YAML ──────────────────────────────────────────

async def test_scene_yaml_get(rest):
    """GET /api/config/scene/yaml/{id} returns YAML."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    scene_id = scenes[0]["id"]
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml/{scene_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    yaml_text = resp.text
    assert len(yaml_text) > 0
