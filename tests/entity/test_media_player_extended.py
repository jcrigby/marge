"""
CTS -- Media Player Extended Service Tests

Tests media_player services: play/pause/stop, next/previous track,
select_source, volume_set, volume_mute, shuffle_set, repeat_set,
and the full media playback lifecycle.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_media_player_play(rest):
    """media_player.media_play sets state to playing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{tag}"
    await rest.set_state(eid, "paused")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/media_play",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


async def test_media_player_pause(rest):
    """media_player.media_pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpp_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/media_pause",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_media_player_stop(rest):
    """media_player.media_stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mps_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/media_stop",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_media_player_next_track(rest):
    """media_player.media_next_track preserves state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpn_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/media_next_track",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


async def test_media_player_previous_track(rest):
    """media_player.media_previous_track preserves state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mppt_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/media_previous_track",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


async def test_media_player_select_source(rest):
    """media_player.select_source stores source attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpss_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/select_source",
        json={"entity_id": eid, "source": "Spotify"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["attributes"]["source"] == "Spotify"


async def test_media_player_volume_set(rest):
    """media_player.volume_set stores volume_level attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpvs_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/volume_set",
        json={"entity_id": eid, "volume_level": 0.75},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.75


async def test_media_player_volume_mute(rest):
    """media_player.volume_mute stores is_volume_muted attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpvm_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/volume_mute",
        json={"entity_id": eid, "is_volume_muted": True},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["attributes"]["is_volume_muted"] is True


async def test_media_player_shuffle_set(rest):
    """media_player.shuffle_set stores shuffle attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpsh_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/shuffle_set",
        json={"entity_id": eid, "shuffle": True},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["attributes"]["shuffle"] is True


async def test_media_player_repeat_set(rest):
    """media_player.repeat_set stores repeat attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mprp_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/repeat_set",
        json={"entity_id": eid, "repeat": "all"},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["attributes"]["repeat"] == "all"


async def test_media_player_turn_on_with_source(rest):
    """media_player.turn_on with source stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mpon_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/turn_on",
        json={"entity_id": eid, "source": "HDMI1"},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["source"] == "HDMI1"


async def test_media_player_lifecycle(rest):
    """Media player lifecycle: off → on → playing → paused → stopped."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mplc_{tag}"
    await rest.set_state(eid, "off")

    for service, expected in [
        ("turn_on", "on"),
        ("media_play", "playing"),
        ("media_pause", "paused"),
        ("media_play", "playing"),
        ("media_stop", "idle"),
        ("turn_off", "off"),
    ]:
        await rest.client.post(
            f"{rest.base_url}/api/services/media_player/{service}",
            json={"entity_id": eid},
            headers=rest._headers(),
        )
        state = await rest.get_state(eid)
        assert state["state"] == expected, f"After {service}: expected {expected}"
