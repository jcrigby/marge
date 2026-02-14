"""
CTS -- Media Player, Lock, Camera, Group Extended Service Tests

Tests service handlers for: media_player (play_media, select_sound_mode),
lock (open), camera (enable/disable_motion_detection), group (set),
update (skip), and generic service fallback for unknown domains.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Media Player Extended ──────────────────────────────

async def test_media_player_play_media(rest):
    """media_player.play_media sets state to playing and stores content attrs."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.mp_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/play_media",
        json={
            "entity_id": eid,
            "media_content_id": "spotify:track:abc123",
            "media_content_type": "music",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:abc123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_media_player_select_sound_mode(rest):
    """media_player.select_sound_mode stores sound_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.sm_{tag}"
    await rest.set_state(eid, "playing")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/media_player/select_sound_mode",
        json={"entity_id": eid, "sound_mode": "surround"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["sound_mode"] == "surround"


# ── Lock Extended ──────────────────────────────────────

async def test_lock_open(rest):
    """lock.open sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.lo_{tag}"
    await rest.set_state(eid, "locked")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/lock/open",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_lock_unlock_then_open(rest):
    """lock.unlock then lock.open: state goes locked → unlocked → open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ulo_{tag}"
    await rest.set_state(eid, "locked")

    await rest.client.post(
        f"{rest.base_url}/api/services/lock/unlock",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    s1 = await rest.get_state(eid)
    assert s1["state"] == "unlocked"

    await rest.client.post(
        f"{rest.base_url}/api/services/lock/open",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    s2 = await rest.get_state(eid)
    assert s2["state"] == "open"


# ── Camera Extended ────────────────────────────────────

async def test_camera_enable_motion_detection(rest):
    """camera.enable_motion_detection sets motion_detection attribute to true."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.em_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/camera/enable_motion_detection",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is True


async def test_camera_disable_motion_detection(rest):
    """camera.disable_motion_detection sets motion_detection attribute to false."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.dm_{tag}"
    await rest.set_state(eid, "streaming", {"motion_detection": True})

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/camera/disable_motion_detection",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is False


async def test_camera_motion_preserves_state(rest):
    """camera.enable_motion_detection preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.mp_{tag}"
    await rest.set_state(eid, "streaming")

    await rest.client.post(
        f"{rest.base_url}/api/services/camera/enable_motion_detection",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "streaming"
    assert state["attributes"]["motion_detection"] is True


# ── Group ──────────────────────────────────────────────

async def test_group_set_state(rest):
    """group.set changes group state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.g_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/group/set",
        json={"entity_id": eid, "state": "on"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_group_set_default_on(rest):
    """group.set without state param defaults to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.gd_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/group/set",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Update Extended ────────────────────────────────────

async def test_update_skip(rest):
    """update.skip sets state to skipped."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.us_{tag}"
    await rest.set_state(eid, "available")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/update/skip",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "skipped"


# ── Generic Service Fallback ───────────────────────────

async def test_generic_turn_on_unknown_domain(rest):
    """Generic turn_on fallback works on any domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.entity_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/custom_domain/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_generic_turn_off_unknown_domain(rest):
    """Generic turn_off fallback works on any domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.entity2_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/custom_domain/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_generic_toggle_unknown_domain(rest):
    """Generic toggle fallback flips on→off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"custom_domain.entity3_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/custom_domain/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "off"
