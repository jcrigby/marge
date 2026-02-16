"""
CTS -- Media Player Entity Tests

Tests media_player domain services: turn_on, turn_off, play, pause, stop,
volume_set, select_source, next/prev track, mute, shuffle, repeat,
play_media, select_sound_mode.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── State-transition services (parametrized) ────────────────

@pytest.mark.parametrize("initial_state,service,expected_state", [
    ("off", "turn_on", "on"),
    ("playing", "turn_off", "off"),
    ("paused", "media_play", "playing"),
    ("playing", "media_pause", "paused"),
    ("playing", "media_stop", "idle"),
])
async def test_media_player_state_transition(rest, initial_state, service, expected_state):
    """media_player service sets expected state."""
    entity_id = f"media_player.test_{service}"
    await rest.set_state(entity_id, initial_state)
    await rest.call_service("media_player", service, {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == expected_state


# ── Track navigation (preserves state, parametrized) ────────

@pytest.mark.parametrize("service", [
    "media_next_track",
    "media_previous_track",
])
async def test_media_player_track_navigation(rest, service):
    """media_player.media_next/previous_track preserves playing state."""
    entity_id = f"media_player.test_{service}"
    await rest.set_state(entity_id, "playing")
    await rest.call_service("media_player", service, {"entity_id": entity_id})

    state = await rest.get_state(entity_id)
    assert state["state"] == "playing"


# ── Attribute-setting services (parametrized) ────────────────

@pytest.mark.parametrize("service,service_data,attr_key,expected_value", [
    ("volume_set", {"volume_level": 0.8}, "volume_level", 0.8),
    ("select_source", {"source": "Bluetooth"}, "source", "Bluetooth"),
    ("volume_mute", {"is_volume_muted": True}, "is_volume_muted", True),
    ("shuffle_set", {"shuffle": True}, "shuffle", True),
    ("repeat_set", {"repeat": "all"}, "repeat", "all"),
    ("select_sound_mode", {"sound_mode": "surround"}, "sound_mode", "surround"),
])
async def test_media_player_attribute_service(rest, service, service_data, attr_key, expected_value):
    """media_player service stores expected attribute."""
    entity_id = f"media_player.test_attr_{service}"
    await rest.set_state(entity_id, "on")
    await rest.call_service("media_player", service, {"entity_id": entity_id, **service_data})

    state = await rest.get_state(entity_id)
    assert state["attributes"][attr_key] == expected_value


# ── play_media ───────────────────────────────────────────────

async def test_media_player_play_media(rest):
    """play_media sets state to playing with content attributes."""
    entity_id = "media_player.test_play_media"
    await rest.set_state(entity_id, "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": entity_id,
        "media_content_id": "spotify:track:123",
        "media_content_type": "music",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:123"
    assert state["attributes"]["media_content_type"] == "music"


# ── turn_on with source ─────────────────────────────────────

async def test_media_player_turn_on_with_source(rest):
    """turn_on with source attribute stores source."""
    entity_id = "media_player.test_on_src"
    await rest.set_state(entity_id, "off")
    await rest.call_service("media_player", "turn_on", {
        "entity_id": entity_id,
        "source": "Radio",
    })
    state = await rest.get_state(entity_id)
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "Radio"
