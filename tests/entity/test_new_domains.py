"""
CTS -- New Domain Service Tests

Tests services for water_heater, humidifier, text, lawn_mower,
remote, and extended climate/media_player/lock services.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Water Heater ──────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature sets temperature attribute."""
    await rest.set_state("water_heater.main", "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": "water_heater.main",
        "temperature": 120,
    })
    state = await rest.get_state("water_heater.main")
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode sets state to mode."""
    await rest.set_state("water_heater.main", "eco")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": "water_heater.main",
        "operation_mode": "performance",
    })
    state = await rest.get_state("water_heater.main")
    assert state["state"] == "performance"


async def test_water_heater_turn_on(rest):
    """water_heater.turn_on sets state to eco."""
    await rest.set_state("water_heater.main", "off")
    await rest.call_service("water_heater", "turn_on", {
        "entity_id": "water_heater.main",
    })
    state = await rest.get_state("water_heater.main")
    assert state["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off sets state to off."""
    await rest.set_state("water_heater.main", "eco")
    await rest.call_service("water_heater", "turn_off", {
        "entity_id": "water_heater.main",
    })
    state = await rest.get_state("water_heater.main")
    assert state["state"] == "off"


# ── Humidifier ────────────────────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier.turn_on sets state to on."""
    await rest.set_state("humidifier.bedroom", "off")
    await rest.call_service("humidifier", "turn_on", {
        "entity_id": "humidifier.bedroom",
    })
    state = await rest.get_state("humidifier.bedroom")
    assert state["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off sets state to off."""
    await rest.set_state("humidifier.bedroom", "on")
    await rest.call_service("humidifier", "turn_off", {
        "entity_id": "humidifier.bedroom",
    })
    state = await rest.get_state("humidifier.bedroom")
    assert state["state"] == "off"


async def test_humidifier_toggle(rest):
    """humidifier.toggle toggles between on/off."""
    await rest.set_state("humidifier.bedroom", "on")
    await rest.call_service("humidifier", "toggle", {
        "entity_id": "humidifier.bedroom",
    })
    state = await rest.get_state("humidifier.bedroom")
    assert state["state"] == "off"


async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity sets humidity attribute."""
    await rest.set_state("humidifier.bedroom", "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": "humidifier.bedroom",
        "humidity": 50,
    })
    state = await rest.get_state("humidifier.bedroom")
    assert state["attributes"]["humidity"] == 50


async def test_humidifier_set_mode(rest):
    """humidifier.set_mode sets mode attribute."""
    await rest.set_state("humidifier.bedroom", "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": "humidifier.bedroom",
        "mode": "sleep",
    })
    state = await rest.get_state("humidifier.bedroom")
    assert state["attributes"]["mode"] == "sleep"


# ── Text ──────────────────────────────────────────────────

async def test_text_set_value(rest):
    """text.set_value sets the entity state."""
    await rest.set_state("text.notes", "")
    await rest.call_service("text", "set_value", {
        "entity_id": "text.notes",
        "value": "Remember to water plants",
    })
    state = await rest.get_state("text.notes")
    assert state["state"] == "Remember to water plants"


# ── Climate turn_on / turn_off ────────────────────────────

async def test_climate_turn_on(rest):
    """climate.turn_on sets state to on."""
    await rest.set_state("climate.office", "off")
    await rest.call_service("climate", "turn_on", {
        "entity_id": "climate.office",
    })
    state = await rest.get_state("climate.office")
    assert state["state"] == "on"


async def test_climate_turn_off(rest):
    """climate.turn_off sets state to off."""
    await rest.set_state("climate.office", "heat")
    await rest.call_service("climate", "turn_off", {
        "entity_id": "climate.office",
    })
    state = await rest.get_state("climate.office")
    assert state["state"] == "off"


# ── Media Player play_media ───────────────────────────────

async def test_media_player_play_media(rest):
    """media_player.play_media sets state to playing with content attributes."""
    await rest.set_state("media_player.tv", "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": "media_player.tv",
        "media_content_id": "spotify:track:abc123",
        "media_content_type": "music",
    })
    state = await rest.get_state("media_player.tv")
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:abc123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_media_player_select_sound_mode(rest):
    """media_player.select_sound_mode sets sound_mode attribute."""
    await rest.set_state("media_player.tv", "playing")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": "media_player.tv",
        "sound_mode": "surround",
    })
    state = await rest.get_state("media_player.tv")
    assert state["attributes"]["sound_mode"] == "surround"


# ── Lock open ─────────────────────────────────────────────

async def test_lock_open(rest):
    """lock.open sets state to open."""
    await rest.set_state("lock.front_gate", "locked")
    await rest.call_service("lock", "open", {
        "entity_id": "lock.front_gate",
    })
    state = await rest.get_state("lock.front_gate")
    assert state["state"] == "open"


# ── Lawn Mower ────────────────────────────────────────────

async def test_lawn_mower_start(rest):
    """lawn_mower.start_mowing sets state to mowing."""
    await rest.set_state("lawn_mower.backyard", "docked")
    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": "lawn_mower.backyard",
    })
    state = await rest.get_state("lawn_mower.backyard")
    assert state["state"] == "mowing"


async def test_lawn_mower_pause(rest):
    """lawn_mower.pause sets state to paused."""
    await rest.set_state("lawn_mower.backyard", "mowing")
    await rest.call_service("lawn_mower", "pause", {
        "entity_id": "lawn_mower.backyard",
    })
    state = await rest.get_state("lawn_mower.backyard")
    assert state["state"] == "paused"


async def test_lawn_mower_dock(rest):
    """lawn_mower.dock sets state to docked."""
    await rest.set_state("lawn_mower.backyard", "mowing")
    await rest.call_service("lawn_mower", "dock", {
        "entity_id": "lawn_mower.backyard",
    })
    state = await rest.get_state("lawn_mower.backyard")
    assert state["state"] == "docked"


# ── Remote ────────────────────────────────────────────────

async def test_remote_turn_on(rest):
    """remote.turn_on sets state to on."""
    await rest.set_state("remote.tv_remote", "off")
    await rest.call_service("remote", "turn_on", {
        "entity_id": "remote.tv_remote",
    })
    state = await rest.get_state("remote.tv_remote")
    assert state["state"] == "on"


async def test_remote_turn_off(rest):
    """remote.turn_off sets state to off."""
    await rest.set_state("remote.tv_remote", "on")
    await rest.call_service("remote", "turn_off", {
        "entity_id": "remote.tv_remote",
    })
    state = await rest.get_state("remote.tv_remote")
    assert state["state"] == "off"


async def test_remote_send_command(rest):
    """remote.send_command stores last_command attribute."""
    await rest.set_state("remote.tv_remote", "on")
    await rest.call_service("remote", "send_command", {
        "entity_id": "remote.tv_remote",
        "command": "volume_up",
    })
    state = await rest.get_state("remote.tv_remote")
    assert state["attributes"]["last_command"] == "volume_up"


# ── Service Listing ───────────────────────────────────────

async def test_services_include_water_heater(rest):
    """GET /api/services includes water_heater domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [s["domain"] for s in resp.json()]
    assert "water_heater" in domains


async def test_services_include_humidifier(rest):
    """GET /api/services includes humidifier domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [s["domain"] for s in resp.json()]
    assert "humidifier" in domains


async def test_services_include_lawn_mower(rest):
    """GET /api/services includes lawn_mower domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [s["domain"] for s in resp.json()]
    assert "lawn_mower" in domains


async def test_services_include_remote(rest):
    """GET /api/services includes remote domain."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    domains = [s["domain"] for s in resp.json()]
    assert "remote" in domains


async def test_services_total_at_least_40(rest):
    """GET /api/services returns at least 40 domains."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    services = resp.json()
    assert len(services) >= 40, f"Expected 40+ domains, got {len(services)}"
