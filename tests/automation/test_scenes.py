"""CTS — Scene tests.

Tests that scene.turn_on applies entity states from scenes.yaml.
"""
import asyncio
import pytest
import httpx

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def set_state(entity_id: str, state: str, attrs: dict | None = None):
    async with httpx.AsyncClient() as c:
        body = {"state": state, "attributes": attrs or {}}
        r = await c.post(f"{BASE}/api/states/{entity_id}", json=body, headers=HEADERS)
        assert r.status_code == 200


async def get_state(entity_id: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states/{entity_id}", headers=HEADERS)
        assert r.status_code == 200
        return r.json()


async def call_service(domain: str, service: str, data: dict):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BASE}/api/services/{domain}/{service}", json=data, headers=HEADERS)
        assert r.status_code == 200
        return r.json()


@pytest.mark.asyncio
async def test_scene_entities_registered():
    """Scene entities should exist in state machine."""
    evening = await get_state("scene.evening")
    assert evening is not None
    goodnight = await get_state("scene.goodnight")
    assert goodnight is not None


@pytest.mark.asyncio
async def test_evening_scene_turns_on_living_room():
    """scene.turn_on for evening should set living room lights with brightness."""
    # Precondition: all target lights off
    lights = [
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
    ]
    for lid in lights:
        await set_state(lid, "off")
    await asyncio.sleep(0.1)

    await call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.1)

    main = await get_state("light.living_room_main")
    assert main["state"] == "on"
    assert main["attributes"]["brightness"] == 180

    accent = await get_state("light.living_room_accent")
    assert accent["state"] == "on"
    assert accent["attributes"]["brightness"] == 120

    lamp = await get_state("light.living_room_lamp")
    assert lamp["state"] == "on"
    assert lamp["attributes"]["brightness"] == 150

    floor = await get_state("light.living_room_floor")
    assert floor["state"] == "on"
    assert floor["attributes"]["brightness"] == 80


@pytest.mark.asyncio
async def test_goodnight_scene_turns_off_all_lights():
    """scene.turn_on for goodnight should turn off all 9 lights."""
    lights = [
        "light.bedroom", "light.bathroom", "light.kitchen",
        "light.living_room_main", "light.living_room_accent",
        "light.living_room_lamp", "light.living_room_floor",
        "light.porch", "light.pathway",
    ]
    for lid in lights:
        await set_state(lid, "on")
    await asyncio.sleep(0.1)

    await call_service("scene", "turn_on", {"entity_id": "scene.goodnight"})
    await asyncio.sleep(0.1)

    for lid in lights:
        s = await get_state(lid)
        assert s["state"] == "off", f"{lid} should be off after goodnight scene"


@pytest.mark.asyncio
async def test_scene_preserves_unrelated_entities():
    """Activating evening scene should not affect entities not in the scene."""
    await set_state("light.bedroom", "on", {"brightness": 200})
    await asyncio.sleep(0.1)

    await call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.1)

    bed = await get_state("light.bedroom")
    assert bed["state"] == "on"
    assert bed["attributes"]["brightness"] == 200


@pytest.mark.asyncio
async def test_evening_scene_applies_rgb_color():
    """scene.turn_on for evening should set rgb_color on accent light."""
    await set_state("light.living_room_accent", "off")
    await asyncio.sleep(0.1)

    await call_service("scene", "turn_on", {"entity_id": "scene.evening"})
    await asyncio.sleep(0.1)

    accent = await get_state("light.living_room_accent")
    assert accent["state"] == "on"
    assert accent["attributes"]["rgb_color"] == [255, 147, 41]
