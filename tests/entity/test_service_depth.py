"""
CTS -- Service Domain Depth Tests

Tests under-covered service handlers: water_heater, humidifier,
lawn_mower, remote, camera, device_tracker, vacuum (deeper),
cover (open/close/stop), climate (swing_mode, turn_on/off),
fan (set_percentage), media_player (play_media, sound_mode,
repeat_set, next/prev track), lock (open).
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Water Heater ──────────────────────────────────────────

async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature sets temperature attribute."""
    await rest.set_state("water_heater.sd_wh", "eco")
    await rest.call_service("water_heater", "set_temperature", {
        "entity_id": "water_heater.sd_wh",
        "temperature": 120,
    })
    state = await rest.get_state("water_heater.sd_wh")
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode changes state."""
    await rest.set_state("water_heater.sd_wh_mode", "eco")
    await rest.call_service("water_heater", "set_operation_mode", {
        "entity_id": "water_heater.sd_wh_mode",
        "operation_mode": "performance",
    })
    state = await rest.get_state("water_heater.sd_wh_mode")
    assert state["state"] == "performance"


async def test_water_heater_turn_on(rest):
    """water_heater.turn_on sets state to eco."""
    await rest.set_state("water_heater.sd_wh_on", "off")
    await rest.call_service("water_heater", "turn_on", {
        "entity_id": "water_heater.sd_wh_on",
    })
    state = await rest.get_state("water_heater.sd_wh_on")
    assert state["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off sets state to off."""
    await rest.set_state("water_heater.sd_wh_off", "eco")
    await rest.call_service("water_heater", "turn_off", {
        "entity_id": "water_heater.sd_wh_off",
    })
    state = await rest.get_state("water_heater.sd_wh_off")
    assert state["state"] == "off"


# ── Humidifier ────────────────────────────────────────────

async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity sets humidity attribute."""
    await rest.set_state("humidifier.sd_hum", "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": "humidifier.sd_hum",
        "humidity": 55,
    })
    state = await rest.get_state("humidifier.sd_hum")
    assert state["attributes"]["humidity"] == 55


async def test_humidifier_set_mode(rest):
    """humidifier.set_mode sets mode attribute."""
    await rest.set_state("humidifier.sd_hum_m", "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": "humidifier.sd_hum_m",
        "mode": "auto",
    })
    state = await rest.get_state("humidifier.sd_hum_m")
    assert state["attributes"]["mode"] == "auto"


async def test_humidifier_toggle(rest):
    """humidifier.toggle flips on/off."""
    await rest.set_state("humidifier.sd_hum_t", "on")
    await rest.call_service("humidifier", "toggle", {
        "entity_id": "humidifier.sd_hum_t",
    })
    state = await rest.get_state("humidifier.sd_hum_t")
    assert state["state"] == "off"


# ── Lawn Mower ────────────────────────────────────────────

async def test_lawn_mower_start_mowing(rest):
    """lawn_mower.start_mowing sets state to mowing."""
    await rest.set_state("lawn_mower.sd_lm", "docked")
    await rest.call_service("lawn_mower", "start_mowing", {
        "entity_id": "lawn_mower.sd_lm",
    })
    state = await rest.get_state("lawn_mower.sd_lm")
    assert state["state"] == "mowing"


async def test_lawn_mower_pause(rest):
    """lawn_mower.pause sets state to paused."""
    await rest.set_state("lawn_mower.sd_lm_p", "mowing")
    await rest.call_service("lawn_mower", "pause", {
        "entity_id": "lawn_mower.sd_lm_p",
    })
    state = await rest.get_state("lawn_mower.sd_lm_p")
    assert state["state"] == "paused"


async def test_lawn_mower_dock(rest):
    """lawn_mower.dock sets state to docked."""
    await rest.set_state("lawn_mower.sd_lm_d", "mowing")
    await rest.call_service("lawn_mower", "dock", {
        "entity_id": "lawn_mower.sd_lm_d",
    })
    state = await rest.get_state("lawn_mower.sd_lm_d")
    assert state["state"] == "docked"


# ── Remote ────────────────────────────────────────────────

async def test_remote_turn_on(rest):
    """remote.turn_on sets state to on."""
    await rest.set_state("remote.sd_rm", "off")
    await rest.call_service("remote", "turn_on", {
        "entity_id": "remote.sd_rm",
    })
    state = await rest.get_state("remote.sd_rm")
    assert state["state"] == "on"


async def test_remote_send_command(rest):
    """remote.send_command stores last_command attribute."""
    await rest.set_state("remote.sd_rm_cmd", "on")
    await rest.call_service("remote", "send_command", {
        "entity_id": "remote.sd_rm_cmd",
        "command": "volume_up",
    })
    state = await rest.get_state("remote.sd_rm_cmd")
    assert state["attributes"]["last_command"] == "volume_up"


# ── Camera ────────────────────────────────────────────────

async def test_camera_turn_on(rest):
    """camera.turn_on sets state to streaming."""
    await rest.set_state("camera.sd_cam", "idle")
    await rest.call_service("camera", "turn_on", {
        "entity_id": "camera.sd_cam",
    })
    state = await rest.get_state("camera.sd_cam")
    assert state["state"] == "streaming"


async def test_camera_turn_off(rest):
    """camera.turn_off sets state to idle."""
    await rest.set_state("camera.sd_cam_off", "streaming")
    await rest.call_service("camera", "turn_off", {
        "entity_id": "camera.sd_cam_off",
    })
    state = await rest.get_state("camera.sd_cam_off")
    assert state["state"] == "idle"


async def test_camera_enable_motion_detection(rest):
    """camera.enable_motion_detection sets attribute."""
    await rest.set_state("camera.sd_cam_md", "idle")
    await rest.call_service("camera", "enable_motion_detection", {
        "entity_id": "camera.sd_cam_md",
    })
    state = await rest.get_state("camera.sd_cam_md")
    assert state["attributes"]["motion_detection"] is True


async def test_camera_disable_motion_detection(rest):
    """camera.disable_motion_detection sets attribute."""
    await rest.set_state("camera.sd_cam_md2", "idle")
    await rest.call_service("camera", "enable_motion_detection", {
        "entity_id": "camera.sd_cam_md2",
    })
    await rest.call_service("camera", "disable_motion_detection", {
        "entity_id": "camera.sd_cam_md2",
    })
    state = await rest.get_state("camera.sd_cam_md2")
    assert state["attributes"]["motion_detection"] is False


# ── Device Tracker ────────────────────────────────────────

async def test_device_tracker_see(rest):
    """device_tracker.see sets state to location_name."""
    await rest.set_state("device_tracker.sd_dt", "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": "device_tracker.sd_dt",
        "location_name": "work",
    })
    state = await rest.get_state("device_tracker.sd_dt")
    assert state["state"] == "work"
    assert state["attributes"]["location_name"] == "work"


async def test_device_tracker_see_with_gps(rest):
    """device_tracker.see with gps sets gps attribute."""
    await rest.set_state("device_tracker.sd_dt_gps", "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": "device_tracker.sd_dt_gps",
        "location_name": "office",
        "gps": [40.39, -111.85],
    })
    state = await rest.get_state("device_tracker.sd_dt_gps")
    assert state["attributes"]["gps"] == [40.39, -111.85]


# ── Vacuum (deeper) ──────────────────────────────────────

async def test_vacuum_return_to_base(rest):
    """vacuum.return_to_base sets state to returning."""
    await rest.set_state("vacuum.sd_vac", "cleaning")
    await rest.call_service("vacuum", "return_to_base", {
        "entity_id": "vacuum.sd_vac",
    })
    state = await rest.get_state("vacuum.sd_vac")
    assert state["state"] == "returning"


async def test_vacuum_pause(rest):
    """vacuum.pause sets state to paused."""
    await rest.set_state("vacuum.sd_vac_p", "cleaning")
    await rest.call_service("vacuum", "pause", {
        "entity_id": "vacuum.sd_vac_p",
    })
    state = await rest.get_state("vacuum.sd_vac_p")
    assert state["state"] == "paused"


# ── Cover (open/close/stop) ──────────────────────────────

async def test_cover_open_sets_position_100(rest):
    """cover.open_cover sets current_position to 100."""
    await rest.set_state("cover.sd_cov", "closed")
    await rest.call_service("cover", "open_cover", {
        "entity_id": "cover.sd_cov",
    })
    state = await rest.get_state("cover.sd_cov")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_close_sets_position_0(rest):
    """cover.close_cover sets current_position to 0."""
    await rest.set_state("cover.sd_cov_c", "open")
    await rest.call_service("cover", "close_cover", {
        "entity_id": "cover.sd_cov_c",
    })
    state = await rest.get_state("cover.sd_cov_c")
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_stop_preserves_state(rest):
    """cover.stop_cover preserves current state."""
    await rest.set_state("cover.sd_cov_s", "open")
    await rest.call_service("cover", "stop_cover", {
        "entity_id": "cover.sd_cov_s",
    })
    state = await rest.get_state("cover.sd_cov_s")
    assert state["state"] == "open"


async def test_cover_position_0_sets_closed(rest):
    """cover.set_cover_position at 0 sets closed."""
    await rest.set_state("cover.sd_cov_p0", "open")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.sd_cov_p0",
        "position": 0,
    })
    state = await rest.get_state("cover.sd_cov_p0")
    assert state["state"] == "closed"


async def test_cover_position_nonzero_sets_open(rest):
    """cover.set_cover_position at 75 sets open."""
    await rest.set_state("cover.sd_cov_p75", "closed")
    await rest.call_service("cover", "set_cover_position", {
        "entity_id": "cover.sd_cov_p75",
        "position": 75,
    })
    state = await rest.get_state("cover.sd_cov_p75")
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 75


# ── Climate (swing_mode, turn_on/off) ────────────────────

async def test_climate_set_swing_mode(rest):
    """climate.set_swing_mode sets swing_mode attribute."""
    await rest.set_state("climate.sd_clim_sw", "heat")
    await rest.call_service("climate", "set_swing_mode", {
        "entity_id": "climate.sd_clim_sw",
        "swing_mode": "vertical",
    })
    state = await rest.get_state("climate.sd_clim_sw")
    assert state["attributes"]["swing_mode"] == "vertical"


async def test_climate_turn_on(rest):
    """climate.turn_on sets state to on."""
    await rest.set_state("climate.sd_clim_on", "off")
    await rest.call_service("climate", "turn_on", {
        "entity_id": "climate.sd_clim_on",
    })
    state = await rest.get_state("climate.sd_clim_on")
    assert state["state"] == "on"


async def test_climate_turn_off(rest):
    """climate.turn_off sets state to off."""
    await rest.set_state("climate.sd_clim_off", "heat")
    await rest.call_service("climate", "turn_off", {
        "entity_id": "climate.sd_clim_off",
    })
    state = await rest.get_state("climate.sd_clim_off")
    assert state["state"] == "off"


# ── Fan (set_percentage) ─────────────────────────────────

async def test_fan_set_percentage_turns_on(rest):
    """fan.set_percentage >0 sets state on."""
    await rest.set_state("fan.sd_fan_pct", "off")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": "fan.sd_fan_pct",
        "percentage": 50,
    })
    state = await rest.get_state("fan.sd_fan_pct")
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 50


async def test_fan_set_percentage_zero_turns_off(rest):
    """fan.set_percentage 0 sets state off."""
    await rest.set_state("fan.sd_fan_pct0", "on")
    await rest.call_service("fan", "set_percentage", {
        "entity_id": "fan.sd_fan_pct0",
        "percentage": 0,
    })
    state = await rest.get_state("fan.sd_fan_pct0")
    assert state["state"] == "off"


# ── Media Player (play_media, sound_mode, repeat, track) ─

async def test_media_player_play_media(rest):
    """media_player.play_media sets content attributes."""
    await rest.set_state("media_player.sd_mp_pm", "idle")
    await rest.call_service("media_player", "play_media", {
        "entity_id": "media_player.sd_mp_pm",
        "media_content_id": "spotify:track:123",
        "media_content_type": "music",
    })
    state = await rest.get_state("media_player.sd_mp_pm")
    assert state["state"] == "playing"
    assert state["attributes"]["media_content_id"] == "spotify:track:123"
    assert state["attributes"]["media_content_type"] == "music"


async def test_media_player_select_sound_mode(rest):
    """media_player.select_sound_mode sets attribute."""
    await rest.set_state("media_player.sd_mp_sm", "playing")
    await rest.call_service("media_player", "select_sound_mode", {
        "entity_id": "media_player.sd_mp_sm",
        "sound_mode": "surround",
    })
    state = await rest.get_state("media_player.sd_mp_sm")
    assert state["attributes"]["sound_mode"] == "surround"


async def test_media_player_repeat_set(rest):
    """media_player.repeat_set sets repeat attribute."""
    await rest.set_state("media_player.sd_mp_rep", "playing")
    await rest.call_service("media_player", "repeat_set", {
        "entity_id": "media_player.sd_mp_rep",
        "repeat": "all",
    })
    state = await rest.get_state("media_player.sd_mp_rep")
    assert state["attributes"]["repeat"] == "all"


async def test_media_player_next_track(rest):
    """media_player.media_next_track preserves state."""
    await rest.set_state("media_player.sd_mp_next", "playing")
    await rest.call_service("media_player", "media_next_track", {
        "entity_id": "media_player.sd_mp_next",
    })
    state = await rest.get_state("media_player.sd_mp_next")
    assert state["state"] == "playing"


async def test_media_player_previous_track(rest):
    """media_player.media_previous_track preserves state."""
    await rest.set_state("media_player.sd_mp_prev", "playing")
    await rest.call_service("media_player", "media_previous_track", {
        "entity_id": "media_player.sd_mp_prev",
    })
    state = await rest.get_state("media_player.sd_mp_prev")
    assert state["state"] == "playing"


# ── Lock (open) ──────────────────────────────────────────

async def test_lock_open(rest):
    """lock.open sets state to open."""
    await rest.set_state("lock.sd_lock_open", "locked")
    await rest.call_service("lock", "open", {
        "entity_id": "lock.sd_lock_open",
    })
    state = await rest.get_state("lock.sd_lock_open")
    assert state["state"] == "open"


# ── Climate temperature range ────────────────────────────

async def test_climate_set_temp_high_low(rest):
    """climate.set_temperature with target_temp_high/low."""
    await rest.set_state("climate.sd_clim_hl", "auto")
    await rest.call_service("climate", "set_temperature", {
        "entity_id": "climate.sd_clim_hl",
        "target_temp_high": 78,
        "target_temp_low": 68,
    })
    state = await rest.get_state("climate.sd_clim_hl")
    assert state["attributes"]["target_temp_high"] == 78
    assert state["attributes"]["target_temp_low"] == 68
