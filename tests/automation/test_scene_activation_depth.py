"""
CTS -- Scene Activation Depth Tests

Tests scene.turn_on behavior: entity state application, attribute
handling, multiple scenes, and scene entity state tracking.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_evening_scene_sets_states(rest):
    """Evening scene sets configured entity states."""
    # Reset
    await rest.set_state("light.living_room_main", "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.evening"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.2)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


async def test_goodnight_scene_sets_states(rest):
    """Goodnight scene turns things off."""
    await rest.set_state("light.living_room_main", "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.goodnight"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.2)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "off"


async def test_scene_entity_exists(rest):
    """Scene entities exist in state machine."""
    state = await rest.get_state("scene.evening")
    assert state is not None
    assert state["entity_id"] == "scene.evening"


async def test_scene_ws_turn_on(ws, rest):
    """WS call_service scene.turn_on activates scene."""
    await rest.set_state("light.living_room_main", "off")

    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert resp.get("success", False) is True
    await asyncio.sleep(0.2)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


async def test_scene_config_list(rest):
    """GET /api/config/scene/config lists scenes."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    scenes = resp.json()
    assert isinstance(scenes, list)
    assert len(scenes) >= 2


async def test_scene_config_has_name(rest):
    """Scene config entries have name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    names = [s.get("name", "") for s in scenes]
    assert "Evening" in names or "evening" in [n.lower() for n in names]


async def test_scene_config_has_entity_count(rest):
    """Scene config entries have entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for s in scenes:
        assert "entity_count" in s
        assert s["entity_count"] >= 0


async def test_scene_yaml_has_content(rest):
    """GET /api/config/scene/yaml returns YAML content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.text) > 20


async def test_scene_sequential_activation(rest):
    """Activating scenes sequentially applies latest."""
    await rest.set_state("light.living_room_main", "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.evening"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.2)
    s1 = await rest.get_state("light.living_room_main")
    assert s1["state"] == "on"

    await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.goodnight"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.2)
    s2 = await rest.get_state("light.living_room_main")
    assert s2["state"] == "off"
