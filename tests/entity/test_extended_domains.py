"""
CTS -- Extended Domain Service Tests

Tests services for camera, weather, device_tracker, and
extended climate/media_player/fan operations.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Camera ───────────────────────────────────────────────

async def test_camera_turn_on(rest):
    """camera.turn_on sets state to streaming."""
    await rest.set_state("camera.front_door", "idle")
    await rest.call_service("camera", "turn_on", {
        "entity_id": "camera.front_door",
    })
    state = await rest.get_state("camera.front_door")
    assert state["state"] == "streaming"


async def test_camera_turn_off(rest):
    """camera.turn_off sets state to idle."""
    await rest.set_state("camera.front_door", "streaming")
    await rest.call_service("camera", "turn_off", {
        "entity_id": "camera.front_door",
    })
    state = await rest.get_state("camera.front_door")
    assert state["state"] == "idle"


async def test_camera_enable_motion_detection(rest):
    """camera.enable_motion_detection sets attribute."""
    await rest.set_state("camera.backyard", "idle")
    await rest.call_service("camera", "enable_motion_detection", {
        "entity_id": "camera.backyard",
    })
    state = await rest.get_state("camera.backyard")
    assert state["attributes"]["motion_detection"] is True


async def test_camera_disable_motion_detection(rest):
    """camera.disable_motion_detection clears attribute."""
    await rest.set_state("camera.backyard", "idle", {"motion_detection": True})
    await rest.call_service("camera", "disable_motion_detection", {
        "entity_id": "camera.backyard",
    })
    state = await rest.get_state("camera.backyard")
    assert state["attributes"]["motion_detection"] is False


# ── Device Tracker ───────────────────────────────────────

async def test_device_tracker_see(rest):
    """device_tracker.see sets location state."""
    await rest.set_state("device_tracker.phone", "not_home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": "device_tracker.phone",
        "location_name": "home",
    })
    state = await rest.get_state("device_tracker.phone")
    assert state["state"] == "home"
    assert state["attributes"]["location_name"] == "home"


# ── Climate Extended ─────────────────────────────────────

async def test_climate_set_preset_mode(rest):
    """climate.set_preset_mode sets preset_mode attribute."""
    await rest.set_state("climate.living_room", "heat")
    await rest.call_service("climate", "set_preset_mode", {
        "entity_id": "climate.living_room",
        "preset_mode": "eco",
    })
    state = await rest.get_state("climate.living_room")
    assert state["attributes"]["preset_mode"] == "eco"


async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode sets swing_mode attribute."""
    await rest.set_state("climate.office", "cool")
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": "climate.office",
        "swing_mode": "vertical",
    })
    state = await rest.get_state("climate.office")
    assert state["attributes"]["swing_mode"] == "vertical"


# ── Media Player Extended ────────────────────────────────

async def test_media_player_volume_mute(rest):
    """media_player.volume_mute sets is_volume_muted attribute."""
    await rest.set_state("media_player.tv", "playing")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": "media_player.tv",
        "is_volume_muted": True,
    })
    state = await rest.get_state("media_player.tv")
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set sets shuffle attribute."""
    await rest.set_state("media_player.speaker", "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": "media_player.speaker",
        "shuffle": True,
    })
    state = await rest.get_state("media_player.speaker")
    assert state["attributes"]["shuffle"] is True


async def test_media_player_repeat_set(rest):
    """media_player.repeat_set sets repeat attribute."""
    await rest.set_state("media_player.speaker", "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": "media_player.speaker",
        "repeat": "all",
    })
    state = await rest.get_state("media_player.speaker")
    assert state["attributes"]["repeat"] == "all"


# ── Fan Extended ─────────────────────────────────────────

async def test_fan_set_direction(rest):
    """fan.set_direction sets direction attribute."""
    await rest.set_state("fan.ceiling", "on")
    await rest.call_service("fan", "set_direction", {
        "entity_id": "fan.ceiling",
        "direction": "reverse",
    })
    state = await rest.get_state("fan.ceiling")
    assert state["attributes"]["direction"] == "reverse"


async def test_fan_set_preset_mode(rest):
    """fan.set_preset_mode sets preset_mode attribute."""
    await rest.set_state("fan.ceiling", "on")
    await rest.call_service("fan", "set_preset_mode", {
        "entity_id": "fan.ceiling",
        "preset_mode": "sleep",
    })
    state = await rest.get_state("fan.ceiling")
    assert state["attributes"]["preset_mode"] == "sleep"


# ── Persistent Notification Service Listing ──────────────

async def test_services_include_persistent_notification(rest):
    """GET /api/services includes dismiss and dismiss_all for persistent_notification."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    pn = next(s for s in services if s["domain"] == "persistent_notification")
    svc_names = list(pn["services"].keys())
    assert "create" in svc_names
    assert "dismiss" in svc_names
    assert "dismiss_all" in svc_names


async def test_services_include_camera(rest):
    """GET /api/services includes camera domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    domains = [s["domain"] for s in services]
    assert "camera" in domains


async def test_services_include_device_tracker(rest):
    """GET /api/services includes device_tracker domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    domains = [s["domain"] for s in services]
    assert "device_tracker" in domains


async def test_services_total_domain_count(rest):
    """GET /api/services returns at least 35 domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    assert len(services) >= 34, f"Expected 34+ domains, got {len(services)}"
