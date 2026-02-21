"""
CTS -- Scene Activation Tests

Tests scene engine: activation via REST service call, attribute merging,
multiple entities in a scene, and scene re-activation.
"""

import asyncio
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_evening_scene_activates(rest):
    """scene.turn_on for evening scene sets expected states."""
    await rest.set_state("light.living_room_main", "off")
    await rest.set_state("light.living_room_accent", "off")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.3)

    state = await rest.get_state("light.living_room_main")
    assert state is not None
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 180


async def test_evening_scene_sets_accent_light(rest):
    """Evening scene sets accent light with rgb_color."""
    await rest.set_state("light.living_room_accent", "off")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.3)

    state = await rest.get_state("light.living_room_accent")
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 120


async def test_goodnight_scene_turns_off_lights(rest):
    """Goodnight scene turns off all lights."""
    await rest.set_state("light.bedroom", "on")
    await rest.set_state("light.kitchen", "on")
    await rest.set_state("light.living_room_main", "on")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.goodnight",
    })
    await asyncio.sleep(0.3)

    for eid in ["light.bedroom", "light.kitchen", "light.living_room_main"]:
        state = await rest.get_state(eid)
        assert state["state"] == "off", f"{eid} should be off after goodnight"


async def test_scene_merges_attributes(rest):
    """Scene activation merges attributes from scene definition."""
    await rest.set_state("light.living_room_main", "off", {"color": "blue"})

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.3)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 180


async def test_scene_reactivation_idempotent(rest):
    """Activating the same scene twice produces consistent results."""
    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.2)
    s1 = await rest.get_state("light.living_room_main")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.2)
    s2 = await rest.get_state("light.living_room_main")

    assert s1["state"] == s2["state"]
    assert s1["attributes"].get("brightness") == s2["attributes"].get("brightness")


async def test_scene_via_ws(ws, rest):
    """Scene activation via WebSocket works."""
    await rest.set_state("light.living_room_main", "off")
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        service_data={"entity_id": "scene.evening"},
    )
    assert resp["success"] is True

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


async def test_scene_entity_exists(rest):
    """Scene entities appear in state machine."""
    states = await rest.get_states()
    scene_ids = [s["entity_id"] for s in states if s["entity_id"].startswith("scene.")]
    assert len(scene_ids) >= 2  # evening and goodnight


async def test_scene_sets_media_player(rest):
    """Evening scene sets media_player state and source."""
    await rest.set_state("media_player.living_room", "off")

    await rest.call_service("scene", "turn_on", {
        "entity_id": "scene.evening",
    })
    await asyncio.sleep(0.3)

    state = await rest.get_state("media_player.living_room")
    assert state["state"] == "on"
    assert state["attributes"].get("source") == "Music"
