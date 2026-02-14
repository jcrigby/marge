"""
CTS -- Miscellaneous Domain Service Handler Tests

Tests service handlers for less common domains: lawn_mower, remote,
water_heater, camera, device_tracker, update, text, input_datetime,
counter reset, group.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Lawn Mower ───────────────────────────────────────────

async def test_lawn_mower_start(rest):
    """lawn_mower start_mowing sets state to mowing."""
    await rest.set_state("lawn_mower.depth_lm", "docked")
    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": "lawn_mower.depth_lm",
    })
    state = await rest.get_state("lawn_mower.depth_lm")
    assert state["state"] == "mowing"


async def test_lawn_mower_pause(rest):
    """lawn_mower pause sets state to paused."""
    await rest.set_state("lawn_mower.depth_lmp", "mowing")
    await rest.call_service("lawn_mower", "pause", {
        "entity_id": "lawn_mower.depth_lmp",
    })
    state = await rest.get_state("lawn_mower.depth_lmp")
    assert state["state"] == "paused"


async def test_lawn_mower_dock(rest):
    """lawn_mower dock sets state to docked."""
    await rest.set_state("lawn_mower.depth_lmd", "mowing")
    await rest.call_service("lawn_mower", "dock", {
        "entity_id": "lawn_mower.depth_lmd",
    })
    state = await rest.get_state("lawn_mower.depth_lmd")
    assert state["state"] == "docked"


# ── Remote ───────────────────────────────────────────────

async def test_remote_turn_on(rest):
    """remote turn_on sets state to on."""
    await rest.set_state("remote.depth_ron", "off")
    await rest.call_service("remote", "turn_on", {"entity_id": "remote.depth_ron"})
    state = await rest.get_state("remote.depth_ron")
    assert state["state"] == "on"


async def test_remote_send_command(rest):
    """remote send_command stores last_command attribute."""
    await rest.set_state("remote.depth_rcmd", "on")
    await rest.call_service("remote", "send_command", {
        "entity_id": "remote.depth_rcmd",
        "command": "power",
    })
    state = await rest.get_state("remote.depth_rcmd")
    assert state["attributes"]["last_command"] == "power"


# ── Water Heater ─────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater set_temperature stores temperature."""
    await rest.set_state("water_heater.depth_wht", "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": "water_heater.depth_wht",
        "temperature": 120,
    })
    state = await rest.get_state("water_heater.depth_wht")
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_operation_mode(rest):
    """water_heater set_operation_mode changes state."""
    await rest.set_state("water_heater.depth_whom", "eco")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": "water_heater.depth_whom",
        "operation_mode": "performance",
    })
    state = await rest.get_state("water_heater.depth_whom")
    assert state["state"] == "performance"


async def test_water_heater_turn_off(rest):
    """water_heater turn_off sets state to off."""
    await rest.set_state("water_heater.depth_whoff", "eco")
    await rest.call_service("water_heater", "turn_off", {
        "entity_id": "water_heater.depth_whoff",
    })
    state = await rest.get_state("water_heater.depth_whoff")
    assert state["state"] == "off"


# ── Camera ───────────────────────────────────────────────

async def test_camera_turn_on(rest):
    """camera turn_on sets state to streaming."""
    await rest.set_state("camera.depth_cam", "idle")
    await rest.call_service("camera", "turn_on", {"entity_id": "camera.depth_cam"})
    state = await rest.get_state("camera.depth_cam")
    assert state["state"] == "streaming"


async def test_camera_turn_off(rest):
    """camera turn_off sets state to idle."""
    await rest.set_state("camera.depth_camoff", "streaming")
    await rest.call_service("camera", "turn_off", {"entity_id": "camera.depth_camoff"})
    state = await rest.get_state("camera.depth_camoff")
    assert state["state"] == "idle"


async def test_camera_enable_motion_detection(rest):
    """camera enable_motion_detection sets motion_detection attribute."""
    await rest.set_state("camera.depth_md", "idle")
    await rest.call_service("camera", "enable_motion_detection", {
        "entity_id": "camera.depth_md",
    })
    state = await rest.get_state("camera.depth_md")
    assert state["attributes"]["motion_detection"] is True


async def test_camera_disable_motion_detection(rest):
    """camera disable_motion_detection clears motion_detection attribute."""
    await rest.set_state("camera.depth_dmd", "idle", {"motion_detection": True})
    await rest.call_service("camera", "disable_motion_detection", {
        "entity_id": "camera.depth_dmd",
    })
    state = await rest.get_state("camera.depth_dmd")
    assert state["attributes"]["motion_detection"] is False


# ── Device Tracker ───────────────────────────────────────

async def test_device_tracker_see(rest):
    """device_tracker see sets location_name state."""
    await rest.set_state("device_tracker.depth_dt", "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": "device_tracker.depth_dt",
        "location_name": "work",
    })
    state = await rest.get_state("device_tracker.depth_dt")
    assert state["state"] == "work"
    assert state["attributes"]["location_name"] == "work"


# ── Update ───────────────────────────────────────────────

async def test_update_install(rest):
    """update install sets state to installing."""
    await rest.set_state("update.depth_upd", "available")
    await rest.call_service("update", "install", {"entity_id": "update.depth_upd"})
    state = await rest.get_state("update.depth_upd")
    assert state["state"] == "installing"


async def test_update_skip(rest):
    """update skip sets state to skipped."""
    await rest.set_state("update.depth_skip", "available")
    await rest.call_service("update", "skip", {"entity_id": "update.depth_skip"})
    state = await rest.get_state("update.depth_skip")
    assert state["state"] == "skipped"


# ── Text ─────────────────────────────────────────────────

async def test_text_set_value(rest):
    """text set_value stores value as state."""
    await rest.set_state("text.depth_txt", "")
    await rest.call_service("text", "set_value", {
        "entity_id": "text.depth_txt",
        "value": "hello world",
    })
    state = await rest.get_state("text.depth_txt")
    assert state["state"] == "hello world"


# ── Input Datetime ───────────────────────────────────────

async def test_input_datetime_set(rest):
    """input_datetime set_datetime stores datetime as state."""
    await rest.set_state("input_datetime.depth_idt", "")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": "input_datetime.depth_idt",
        "datetime": "2026-02-13 14:30:00",
    })
    state = await rest.get_state("input_datetime.depth_idt")
    assert state["state"] == "2026-02-13 14:30:00"


# ── Counter ──────────────────────────────────────────────

async def test_counter_reset_to_initial(rest):
    """counter reset returns to initial value attribute."""
    await rest.set_state("counter.depth_crst", "5", {"initial": 0})
    await rest.call_service("counter", "reset", {"entity_id": "counter.depth_crst"})
    state = await rest.get_state("counter.depth_crst")
    assert state["state"] == "0"


# ── Group ────────────────────────────────────────────────

async def test_group_set(rest):
    """group set changes state to provided value."""
    await rest.set_state("group.depth_grp", "off")
    await rest.call_service("group", "set", {
        "entity_id": "group.depth_grp",
        "state": "on",
    })
    state = await rest.get_state("group.depth_grp")
    assert state["state"] == "on"
