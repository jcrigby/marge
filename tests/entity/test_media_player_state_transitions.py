"""
CTS -- Media Player State Transition Tests

Tests media_player service calls and their state transitions:
play, pause, stop, next_track, previous_track, volume controls,
source selection, and mute toggling.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_media_player_play(rest):
    """media_player.media_play sets state to 'playing'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("media_player", "media_play", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "playing"


async def test_media_player_pause(rest):
    """media_player.media_pause sets state to 'paused'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_p_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "media_pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


async def test_media_player_stop(rest):
    """media_player.media_stop sets state to 'idle'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_s_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "media_stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_media_player_next_track(rest):
    """media_player.media_next_track preserves playing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_n_{tag}"
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


async def test_media_player_turn_on(rest):
    """media_player.turn_on sets state to 'on'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_on_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("media_player", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_media_player_turn_off(rest):
    """media_player.turn_off sets state to 'off'."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_off_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_media_player_volume_mute(rest):
    """media_player.volume_mute stores is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_mute_{tag}"
    await rest.set_state(eid, "on")

    await rest.call_service("media_player", "volume_mute", {
        "entity_id": eid,
        "is_volume_muted": True,
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("is_volume_muted") is True


async def test_media_player_repeat_set(rest):
    """media_player.repeat_set stores repeat attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_rep_{tag}"
    await rest.set_state(eid, "playing")

    await rest.call_service("media_player", "repeat_set", {
        "entity_id": eid,
        "repeat": "all",
    })
    state = await rest.get_state(eid)
    assert state["attributes"].get("repeat") == "all"


async def test_media_player_lifecycle(rest):
    """Full media player lifecycle: off → on → playing → paused → idle → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_lc_{tag}"
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
