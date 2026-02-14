"""
CTS -- Media Player Service Handler Depth Tests

Tests media_player domain service handlers: play, pause, stop, next/prev,
select_source, volume, mute, shuffle, repeat, play_media, select_sound_mode.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_media_play(rest):
    """media_play sets state to playing."""
    await rest.set_state("media_player.depth_play", "paused")
    await rest.call_service("media_player", "media_play", {
        "entity_id": "media_player.depth_play",
    })
    state = await rest.get_state("media_player.depth_play")
    assert state["state"] == "playing"


async def test_media_pause(rest):
    """media_pause sets state to paused."""
    await rest.set_state("media_player.depth_pause", "playing")
    await rest.call_service("media_player", "media_pause", {
        "entity_id": "media_player.depth_pause",
    })
    state = await rest.get_state("media_player.depth_pause")
    assert state["state"] == "paused"


async def test_media_stop(rest):
    """media_stop sets state to idle."""
    await rest.set_state("media_player.depth_stop", "playing")
    await rest.call_service("media_player", "media_stop", {
        "entity_id": "media_player.depth_stop",
    })
    state = await rest.get_state("media_player.depth_stop")
    assert state["state"] == "idle"


async def test_media_next_track(rest):
    """media_next_track preserves current state."""
    await rest.set_state("media_player.depth_next", "playing")
    await rest.call_service("media_player", "media_next_track", {
        "entity_id": "media_player.depth_next",
    })
    state = await rest.get_state("media_player.depth_next")
    assert state["state"] == "playing"


async def test_media_previous_track(rest):
    """media_previous_track preserves current state."""
    await rest.set_state("media_player.depth_prev", "playing")
    await rest.call_service("media_player", "media_previous_track", {
        "entity_id": "media_player.depth_prev",
    })
    state = await rest.get_state("media_player.depth_prev")
    assert state["state"] == "playing"


async def test_select_source(rest):
    """select_source stores source attribute."""
    await rest.set_state("media_player.depth_src", "on")
    await rest.call_service("media_player", "select_source", {
        "entity_id": "media_player.depth_src",
        "source": "Spotify",
    })
    state = await rest.get_state("media_player.depth_src")
    assert state["attributes"]["source"] == "Spotify"


async def test_volume_set(rest):
    """volume_set stores volume_level attribute."""
    await rest.set_state("media_player.depth_vol", "on")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": "media_player.depth_vol",
        "volume_level": 0.75,
    })
    state = await rest.get_state("media_player.depth_vol")
    assert state["attributes"]["volume_level"] == 0.75


async def test_volume_mute(rest):
    """volume_mute stores is_volume_muted attribute."""
    await rest.set_state("media_player.depth_mute", "on")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": "media_player.depth_mute",
        "is_volume_muted": True,
    })
    state = await rest.get_state("media_player.depth_mute")
    assert state["attributes"]["is_volume_muted"] is True


async def test_shuffle_set(rest):
    """shuffle_set stores shuffle attribute."""
    await rest.set_state("media_player.depth_shuf", "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": "media_player.depth_shuf",
        "shuffle": True,
    })
    state = await rest.get_state("media_player.depth_shuf")
    assert state["attributes"]["shuffle"] is True


async def test_repeat_set(rest):
    """repeat_set stores repeat attribute."""
    await rest.set_state("media_player.depth_rep", "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": "media_player.depth_rep",
        "repeat": "all",
    })
    state = await rest.get_state("media_player.depth_rep")
    assert state["attributes"]["repeat"] == "all"


async def test_play_media(rest):
    """play_media sets state to playing with content attributes."""
    await rest.set_state("media_player.depth_pm", "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": "media_player.depth_pm",
        "media_content_id": "spotify:track:123",
        "media_content_type": "music",
    })
    state = await rest.get_state("media_player.depth_pm")
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_select_sound_mode(rest):
    """select_sound_mode stores sound_mode attribute."""
    await rest.set_state("media_player.depth_sm", "playing")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": "media_player.depth_sm",
        "sound_mode": "surround",
    })
    state = await rest.get_state("media_player.depth_sm")
    assert state["attributes"]["sound_mode"] == "surround"


async def test_turn_on_with_source(rest):
    """turn_on with source attribute."""
    await rest.set_state("media_player.depth_on", "off")
    await rest.call_service("media_player", "turn_on", {
        "entity_id": "media_player.depth_on",
        "source": "Radio",
    })
    state = await rest.get_state("media_player.depth_on")
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "Radio"
