"""
CTS -- Vacuum and Media Player State Machine Depth Tests

Tests vacuum services (start, stop, pause, return_to_base) and media
player services (play, pause, stop, next/prev track, select_source,
volume_set, volume_mute, shuffle_set, repeat_set) for correct state
transitions and attribute merging.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Vacuum State Transitions ─────────────────────────────

async def test_vacuum_start_cleaning(rest):
    """vacuum.start sets state to cleaning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vs_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "cleaning"


async def test_vacuum_stop_idle(rest):
    """vacuum.stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vst_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_vacuum_pause_paused(rest):
    """vacuum.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vp_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vr_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "returning"


async def test_vacuum_preserves_attributes(rest):
    """Vacuum services preserve existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vattr_{tag}"
    await rest.set_state(eid, "idle", {"battery_level": 85, "fan_speed": "max"})
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "cleaning"
    assert state["attributes"]["battery_level"] == 85
    assert state["attributes"]["fan_speed"] == "max"


async def test_vacuum_full_cycle(rest):
    """Vacuum full cycle: idle → cleaning → paused → cleaning → returning → idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vcycle_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"

    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


# ── Media Player State Transitions ───────────────────────

async def test_media_play(rest):
    """media_player.media_play sets state to playing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


async def test_media_pause(rest):
    """media_player.media_pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpp_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


async def test_media_stop(rest):
    """media_player.media_stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mps_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_media_next_track_preserves_state(rest):
    """media_player.media_next_track preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpn_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_next_track", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


async def test_media_previous_track_preserves_state(rest):
    """media_player.media_previous_track preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mppr_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "media_previous_track", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


# ── Media Player Attribute Services ──────────────────────

async def test_media_select_source(rest):
    """media_player.select_source sets source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsrc_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "select_source", {
        "entity_id": eid, "source": "HDMI 1",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["source"] == "HDMI 1"


async def test_media_volume_set(rest):
    """media_player.volume_set sets volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpvol_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "volume_set", {
        "entity_id": eid, "volume_level": 0.75,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.75


async def test_media_volume_mute(rest):
    """media_player.volume_mute sets is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpmute_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid, "is_volume_muted": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_shuffle_set(rest):
    """media_player.shuffle_set sets shuffle attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpshuf_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "shuffle_set", {
        "entity_id": eid, "shuffle": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["shuffle"] is True


async def test_media_repeat_set(rest):
    """media_player.repeat_set sets repeat attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mprep_{tag}"
    await rest.set_state(eid, "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": eid, "repeat": "all",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["repeat"] == "all"


async def test_media_turn_on_with_source(rest):
    """media_player.turn_on with source sets source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpon_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("media_player", "turn_on", {
        "entity_id": eid, "source": "Bluetooth",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "Bluetooth"


async def test_media_attrs_preserved_across_play(rest):
    """Attributes survive play/pause/stop transitions."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mppres_{tag}"
    await rest.set_state(eid, "on", {"source": "TV", "volume_level": 0.5})
    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["source"] == "TV"
    assert state["attributes"]["volume_level"] == 0.5
