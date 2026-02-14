"""
CTS -- Media Player Entity Tests

Tests media_player domain services: turn_on, turn_off, play, pause, stop,
volume_set, select_source, next/prev track.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_media_player_turn_on(rest):
    """media_player.turn_on sets state to 'on'."""
    entity_id = "media_player.test_on"
    await rest.set_state(entity_id, "off")
    await rest.call_service("media_player", "turn_on", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "on"


async def test_media_player_turn_off(rest):
    """media_player.turn_off sets state to 'off'."""
    entity_id = "media_player.test_off"
    await rest.set_state(entity_id, "playing")
    await rest.call_service("media_player", "turn_off", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "off"


async def test_media_player_play(rest):
    """media_player.media_play sets state to 'playing'."""
    entity_id = "media_player.test_play"
    await rest.set_state(entity_id, "paused")
    await rest.call_service("media_player", "media_play", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "playing"


async def test_media_player_pause(rest):
    """media_player.media_pause sets state to 'paused'."""
    entity_id = "media_player.test_pause"
    await rest.set_state(entity_id, "playing")
    await rest.call_service("media_player", "media_pause", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "paused"


async def test_media_player_stop(rest):
    """media_player.media_stop sets state to 'idle'."""
    entity_id = "media_player.test_stop"
    await rest.set_state(entity_id, "playing")
    await rest.call_service("media_player", "media_stop", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "idle"


async def test_media_player_volume(rest):
    """media_player.volume_set updates volume_level attribute."""
    entity_id = "media_player.test_vol"
    await rest.set_state(entity_id, "on", {"volume_level": 0.5})
    await rest.call_service("media_player", "volume_set", {
        "entity_id": entity_id,
        "volume_level": 0.8,
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["volume_level"] == 0.8


async def test_media_player_select_source(rest):
    """media_player.select_source updates source attribute."""
    entity_id = "media_player.test_src"
    await rest.set_state(entity_id, "on", {"source": "TV"})
    await rest.call_service("media_player", "select_source", {
        "entity_id": entity_id,
        "source": "Bluetooth",
    })

    state = await rest.get_state(entity_id)
    assert state["attributes"]["source"] == "Bluetooth"


async def test_media_player_next_track(rest):
    """media_player.media_next_track preserves playing state."""
    entity_id = "media_player.test_next"
    await rest.set_state(entity_id, "playing")
    await rest.call_service("media_player", "media_next_track", {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "playing"
