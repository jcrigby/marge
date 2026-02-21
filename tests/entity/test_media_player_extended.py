"""
CTS -- Media Player Extended Service Tests

Tests media_player services: play/pause/stop, next/previous track,
select_source, volume_set, volume_mute, shuffle_set, repeat_set,
play_media, select_sound_mode, and the full media playback lifecycle.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── State-transition services (parametrized) ────────────────

@pytest.mark.parametrize("initial_state,service,expected_state", [
    ("off", "turn_on", "on"),
    ("playing", "turn_off", "off"),
    ("paused", "media_play", "playing"),
    ("playing", "media_pause", "paused"),
    ("playing", "media_stop", "idle"),
])
async def test_media_player_state_service(rest, initial_state, service, expected_state):
    """media_player service transitions to expected state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{service}_{tag}"
    await rest.set_state(eid, initial_state)

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/{service}",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    state = await rest.get_state(eid)
    assert state["state"] == expected_state


# ── Track navigation (preserves state, parametrized) ────────

@pytest.mark.parametrize("service", [
    "media_next_track",
    "media_previous_track",
])
async def test_media_player_track_service(rest, service):
    """media_player track navigation preserves playing state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{service}_{tag}"
    await rest.set_state(eid, "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/{service}",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["state"] == "playing"


# ── Attribute-setting services (parametrized) ────────────────

@pytest.mark.parametrize("service,payload,attr_key,expected", [
    ("select_source", {"source": "Spotify"}, "source", "Spotify"),
    ("volume_set", {"volume_level": 0.75}, "volume_level", 0.75),
    ("volume_mute", {"is_volume_muted": True}, "is_volume_muted", True),
    ("shuffle_set", {"shuffle": True}, "shuffle", True),
    ("repeat_set", {"repeat": "all"}, "repeat", "all"),
])
async def test_media_player_attribute_set(rest, service, payload, attr_key, expected):
    """media_player service stores expected attribute via raw HTTP."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{service}_{tag}"
    await rest.set_state(eid, "on" if service in ("select_source", "volume_set", "volume_mute") else "playing")

    await rest.client.post(
        f"{rest.base_url}/api/services/media_player/{service}",
        json={"entity_id": eid, **payload},
        headers=rest._headers(),
    )
    state = await rest.get_state(eid)
    assert state["attributes"][attr_key] == expected


# ── turn_on with source ─────────────────────────────────────

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


# ── Full lifecycle ───────────────────────────────────────────

async def test_media_player_lifecycle(rest):
    """Media player lifecycle: off -> on -> playing -> paused -> stopped."""
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


# ── Merged from depth: play_media ────────────────────────────

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


# ── Merged from depth: select_source preserves state ─────────

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


# ── Merged from depth: select_sound_mode ─────────────────────

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


# ── Merged from depth: volume_unmute ─────────────────────────

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
