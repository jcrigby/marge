"""
CTS -- Scene Engine Depth Tests

Tests the scene engine using the two demo scenes (evening, goodnight):
entity state application, attribute merging (brightness, rgb_color),
scene.turn_on via REST and WS, scene config API format.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Scene Config API ───────────────────────────────────────

async def test_scene_config_returns_200(rest):
    """GET /api/config/scene/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_scene_config_returns_list(rest):
    """Scene config returns a JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2


async def test_scene_config_has_evening(rest):
    """Scene config includes evening scene."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [s["id"] for s in data]
    assert "evening" in ids


async def test_scene_config_has_goodnight(rest):
    """Scene config includes goodnight scene."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [s["id"] for s in data]
    assert "goodnight" in ids


async def test_scene_config_has_fields(rest):
    """Scene entries have id, name, entity_count, entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "id" in scene
        assert "name" in scene
        assert "entity_count" in scene
        assert "entities" in scene


async def test_evening_has_5_entities(rest):
    """Evening scene controls 5 entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    evening = next(s for s in data if s["id"] == "evening")
    assert evening["entity_count"] == 5


async def test_goodnight_has_9_entities(rest):
    """Goodnight scene controls 9 entities (all lights)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    goodnight = next(s for s in data if s["id"] == "goodnight")
    assert goodnight["entity_count"] == 9


# ── Evening Scene Activation ──────────────────────────────

async def test_evening_scene_turns_on_main(rest):
    """Activating evening scene turns on living_room_main."""
    await rest.set_state("light.living_room_main", "off")
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


async def test_evening_scene_sets_main_brightness(rest):
    """Evening scene sets living_room_main brightness to 180."""
    await rest.set_state("light.living_room_main", "off", {"brightness": 0})
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_main")
    assert state["attributes"].get("brightness") == 180


async def test_evening_scene_sets_accent_rgb(rest):
    """Evening scene sets living_room_accent rgb_color."""
    await rest.set_state("light.living_room_accent", "off")
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_accent")
    assert state["state"] == "on"
    assert state["attributes"].get("rgb_color") == [255, 147, 41]


async def test_evening_scene_sets_media_player(rest):
    """Evening scene sets media_player to on with source."""
    await rest.set_state("media_player.living_room", "off")
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.3)
    state = await rest.get_state("media_player.living_room")
    assert state["state"] == "on"
    assert state["attributes"].get("source") == "Music"


# ── Goodnight Scene Activation ────────────────────────────

async def test_goodnight_scene_turns_off_all_lights(rest):
    """Activating goodnight scene turns off all 9 lights."""
    # Set some lights on first
    for light in [
        "light.bedroom", "light.kitchen",
        "light.living_room_main", "light.porch",
    ]:
        await rest.set_state(light, "on")

    await rest.call_service("scene", "turn_on", {"entity_id": "scene.goodnight"})
    await asyncio.sleep(0.3)

    for light in [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
        "light.porch", "light.pathway",
    ]:
        state = await rest.get_state(light)
        assert state["state"] == "off", f"{light} should be off"


# ── Scene Activation Preserves Existing Attributes ────────

async def test_scene_preserves_friendly_name(rest):
    """Scene activation preserves existing friendly_name attribute."""
    await rest.set_state("light.living_room_main", "off", {
        "friendly_name": "Main Light",
        "icon": "mdi:ceiling-light",
    })
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_main")
    assert state["attributes"].get("friendly_name") == "Main Light"


# ── Scene via WS ──────────────────────────────────────────

async def test_scene_via_ws(ws, rest):
    """Activating scene via WS call_service works."""
    await rest.set_state("light.living_room_main", "off")
    result = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert result["success"] is True
    await asyncio.sleep(0.3)
    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"
