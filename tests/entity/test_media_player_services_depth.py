"""
CTS -- Media Player Service Depth Tests

Tests media_player domain services: turn_on, turn_off, media_play,
media_pause, media_stop, media_next/previous_track, select_source,
volume_set, volume_mute, shuffle_set, repeat_set.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic On/Off ─────────────────────────────────────────

async def test_media_player_turn_on(rest):
    """media_player.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("media_player", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_media_player_turn_off(rest):
    """media_player.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_off_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_media_player_turn_on_with_source(rest):
    """media_player.turn_on with source sets source attr."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_src_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("media_player", "turn_on", {
        "entity_id": eid, "source": "Spotify",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "Spotify"


# ── Playback ─────────────────────────────────────────────

async def test_media_player_media_play(rest):
    """media_player.media_play sets state to playing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_play_{tag}"
    await rest.set_state(eid, "paused")
    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


async def test_media_player_media_pause(rest):
    """media_player.media_pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_pause_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_media_player_media_stop(rest):
    """media_player.media_stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_stop_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_stop", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_media_player_next_track_preserves_state(rest):
    """media_player.media_next_track preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_next_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_next_track", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


async def test_media_player_previous_track_preserves_state(rest):
    """media_player.media_previous_track preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_prev_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_previous_track", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


# ── Source/Volume ─────────────────────────────────────────

async def test_media_player_select_source(rest):
    """media_player.select_source sets source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_ssrc_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "select_source", {
        "entity_id": eid, "source": "HDMI 1",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["source"] == "HDMI 1"


async def test_media_player_volume_set(rest):
    """media_player.volume_set sets volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_vol_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid, "volume_level": 0.65,
    })
    state = await rest.get_state(eid)
    assert abs(state["attributes"]["volume_level"] - 0.65) < 0.01


async def test_media_player_volume_mute(rest):
    """media_player.volume_mute sets is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_mute_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid, "is_volume_muted": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set sets shuffle attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_shuf_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": eid, "shuffle": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["shuffle"] is True


async def test_media_player_repeat_set(rest):
    """media_player.repeat_set sets repeat attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsd_rep_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": eid, "repeat": "all",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["repeat"] == "all"
