"""
CTS -- Vacuum, Lawn Mower, Remote, and Water Heater Service Depth Tests

Tests less-common domain services: vacuum (start/stop/pause/return_to_base),
lawn_mower (start_mowing/dock/pause), remote (turn_on/turn_off/send_command),
water_heater (set_temperature/set_operation_mode), camera (turn_on/turn_off).
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Vacuum ─────────────────────────────────────────────────

async def test_vacuum_start(rest):
    """vacuum.start sets state to cleaning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vac_{tag}"
    await rest.set_state(eid, "docked")
    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"


async def test_vacuum_stop(rest):
    """vacuum.stop sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vac_stop_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "stop", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"


async def test_vacuum_pause(rest):
    """vacuum.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vac_pause_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vac_rtb_{tag}"
    await rest.set_state(eid, "cleaning")
    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"


async def test_vacuum_full_lifecycle(rest):
    """Vacuum: docked → cleaning → paused → cleaning → returning."""
    tag = uuid.uuid4().hex[:8]
    eid = f"vacuum.vac_life_{tag}"
    await rest.set_state(eid, "docked")

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"

    await rest.call_service("vacuum", "start", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "cleaning"

    await rest.call_service("vacuum", "return_to_base", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "returning"


# ── Lawn Mower ─────────────────────────────────────────────

async def test_lawn_mower_start(rest):
    """lawn_mower.start_mowing sets state to mowing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.lm_{tag}"
    await rest.set_state(eid, "docked")
    await rest.call_service("lawn_mower", "start_mowing", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "mowing"


async def test_lawn_mower_dock(rest):
    """lawn_mower.dock sets state to docked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.lm_dock_{tag}"
    await rest.set_state(eid, "mowing")
    await rest.call_service("lawn_mower", "dock", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "docked"


async def test_lawn_mower_pause(rest):
    """lawn_mower.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.lm_pause_{tag}"
    await rest.set_state(eid, "mowing")
    await rest.call_service("lawn_mower", "pause", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "paused"


# ── Remote ─────────────────────────────────────────────────

async def test_remote_turn_on(rest):
    """remote.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.rm_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("remote", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_remote_turn_off(rest):
    """remote.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.rm_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("remote", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_remote_send_command(rest):
    """remote.send_command preserves state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.rm_cmd_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("remote", "send_command", {
        "entity_id": eid, "command": "volume_up"
    })
    assert (await rest.get_state(eid))["state"] == "on"


# ── Water Heater ───────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.wh_{tag}"
    await rest.set_state(eid, "electric", {"temperature": 120})
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": eid, "temperature": 130
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 130


async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode changes state to the mode value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.wh_mode_{tag}"
    await rest.set_state(eid, "electric")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": eid, "operation_mode": "eco"
    })
    state = await rest.get_state(eid)
    assert state["state"] == "eco"


# ── Camera ─────────────────────────────────────────────────

async def test_camera_turn_on(rest):
    """camera.turn_on sets state to streaming."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cam_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("camera", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "streaming"


async def test_camera_turn_off(rest):
    """camera.turn_off sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cam_off_{tag}"
    await rest.set_state(eid, "streaming")
    await rest.call_service("camera", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "idle"
