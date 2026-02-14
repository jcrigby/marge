"""
CTS -- Media Player Extra Services Depth Tests

Tests media_player extended services: play_media (content_id,
content_type), select_sound_mode, and combined attribute scenarios.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Play Media ──────────────────────────────────────────

async def test_media_player_play_media(rest):
    """media_player.play_media sets content attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_play_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "spotify:track:abc123",
        "media_content_type": "music",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:abc123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_media_player_play_media_content_id_only(rest):
    """media_player.play_media with content_id only."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_cid_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "http://example.com/stream",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "http://example.com/stream"


async def test_media_player_play_media_preserves_volume(rest):
    """play_media preserves existing volume attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_pvol_{tag}"
    await rest.set_state(eid, "idle", {"volume_level": 0.5})
    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "test",
        "media_content_type": "music",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.5


# ── Select Sound Mode ──────────────────────────────────

async def test_media_player_select_sound_mode(rest):
    """media_player.select_sound_mode sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_sm_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": eid,
        "sound_mode": "surround",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["sound_mode"] == "surround"


async def test_media_player_sound_mode_preserves_state(rest):
    """select_sound_mode preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_smpres_{tag}"
    await rest.set_state(eid, "paused")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": eid,
        "sound_mode": "stereo",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "paused"
    assert state["attributes"]["sound_mode"] == "stereo"


async def test_media_player_sound_mode_movie(rest):
    """select_sound_mode with movie mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_smmov_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": eid,
        "sound_mode": "movie",
    })
    assert (await rest.get_state(eid))["attributes"]["sound_mode"] == "movie"


# ── Combined Scenarios ──────────────────────────────────

async def test_media_player_play_then_sound_mode(rest):
    """Play media then change sound mode preserves content attrs."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_combo_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "test_track",
        "media_content_type": "music",
    })

    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": eid,
        "sound_mode": "surround",
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["media_content_id"] == "test_track"
    assert state["attributes"]["sound_mode"] == "surround"


async def test_media_player_full_media_lifecycle(rest):
    """Media: idle → play_media → pause → play → stop."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mped_lc_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "album_1",
        "media_content_type": "music",
    })
    assert (await rest.get_state(eid))["state"] == "playing"

    await rest.call_service("media_player", "media_pause", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("media_player", "media_play", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "playing"

    await rest.call_service("media_player", "media_stop", {
        "entity_id": eid,
    })
    assert (await rest.get_state(eid))["state"] == "idle"
