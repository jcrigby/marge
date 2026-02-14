"""
CTS -- Media Player Extended Service Depth Tests

Tests media_player services beyond basic on/off: play_media, select_source,
select_sound_mode, volume_set, volume_mute, shuffle_set, repeat_set,
media_play/pause/stop, media_next_track/previous_track, turn_on with source.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── play_media ────────────────────────────────────────────

async def test_media_player_play_media(rest):
    """media_player.play_media sets state to playing and content attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_pm_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "spotify:track:123",
        "media_content_type": "music",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_media_player_play_media_preserves_volume(rest):
    """play_media preserves existing volume attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_pmv_{tag}"
    await rest.set_state(eid, "on", {"volume_level": 0.5})
    await rest.call_service("media_player", "play_media", {
        "entity_id": eid,
        "media_content_id": "radio:fm101",
        "media_content_type": "music",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["volume_level"] == 0.5


# ── select_source ─────────────────────────────────────────

async def test_media_player_select_source(rest):
    """media_player.select_source sets source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_src_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "select_source", {
        "entity_id": eid, "source": "HDMI 2",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["source"] == "HDMI 2"


async def test_media_player_select_source_preserves_state(rest):
    """select_source preserves current playing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_srcp_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "select_source", {
        "entity_id": eid, "source": "Bluetooth",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["source"] == "Bluetooth"


# ── select_sound_mode ─────────────────────────────────────

async def test_media_player_select_sound_mode(rest):
    """media_player.select_sound_mode sets sound_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_sm_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": eid, "sound_mode": "surround",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["sound_mode"] == "surround"


# ── volume_set ────────────────────────────────────────────

async def test_media_player_volume_set(rest):
    """media_player.volume_set sets volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_vol_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid, "volume_level": 0.75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.75
    assert state["state"] == "playing"


# ── volume_mute ───────────────────────────────────────────

async def test_media_player_volume_mute(rest):
    """media_player.volume_mute sets is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_mute_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid, "is_volume_muted": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_player_volume_unmute(rest):
    """media_player.volume_mute can unmute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_unmute_{tag}"
    await rest.set_state(eid, "playing", {"is_volume_muted": True})
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid, "is_volume_muted": False,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is False


# ── shuffle_set ───────────────────────────────────────────

async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set sets shuffle attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_shuf_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": eid, "shuffle": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["shuffle"] is True


# ── repeat_set ────────────────────────────────────────────

async def test_media_player_repeat_set(rest):
    """media_player.repeat_set sets repeat attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_rep_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": eid, "repeat": "all",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["repeat"] == "all"


# ── media_play / pause / stop ─────────────────────────────

async def test_media_player_play_pause_stop_cycle(rest):
    """media_player play → pause → play → stop cycle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_cycle_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"

    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"

    await rest.call_service("media_player", "media_stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── next_track / previous_track ───────────────────────────

async def test_media_player_next_track(rest):
    """media_player.media_next_track preserves playing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_next_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_next_track", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


async def test_media_player_previous_track(rest):
    """media_player.media_previous_track preserves playing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_prev_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_previous_track", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


# ── turn_on with source ──────────────────────────────────

async def test_media_player_turn_on_with_source(rest):
    """media_player.turn_on with source sets source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_onsrc_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("media_player", "turn_on", {
        "entity_id": eid, "source": "TV",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "TV"


# ── Full lifecycle ────────────────────────────────────────

async def test_media_player_full_lifecycle(rest):
    """Full media_player lifecycle: off → on → playing → paused → idle → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_life_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("media_player", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"

    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("media_player", "media_stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"

    await rest.call_service("media_player", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"
