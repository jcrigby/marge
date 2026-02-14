"""
CTS -- Camera, Update, Group, and Weather Service Depth Tests

Tests service handlers for camera (turn_on, turn_off,
enable/disable_motion_detection), update (install, skip),
group (set), weather (get_forecasts stub), device_tracker (see),
and input_datetime (set_datetime).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Camera Services ──────────────────────────────────────

async def test_camera_turn_on_streaming(rest):
    """camera.turn_on sets state to streaming."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cusgs_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("camera", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "streaming"


async def test_camera_turn_off_idle(rest):
    """camera.turn_off sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cusgs_off_{tag}"
    await rest.set_state(eid, "streaming")
    await rest.call_service("camera", "turn_off", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "idle"


async def test_camera_enable_motion_detection(rest):
    """camera.enable_motion_detection sets motion_detection attr to true."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cusgs_emd_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is True


async def test_camera_disable_motion_detection(rest):
    """camera.disable_motion_detection sets motion_detection attr to false."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cusgs_dmd_{tag}"
    await rest.set_state(eid, "streaming")
    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    await rest.call_service("camera", "disable_motion_detection", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is False


async def test_camera_motion_preserves_state(rest):
    """Motion detection toggle preserves current camera state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cusgs_pres_{tag}"
    await rest.set_state(eid, "streaming")
    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "streaming"


# ── Update Services ──────────────────────────────────────

async def test_update_install_state(rest):
    """update.install sets state to installing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.cusgs_inst_{tag}"
    await rest.set_state(eid, "available")
    await rest.call_service("update", "install", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "installing"


async def test_update_skip_state(rest):
    """update.skip sets state to skipped."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.cusgs_skip_{tag}"
    await rest.set_state(eid, "available")
    await rest.call_service("update", "skip", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "skipped"


# ── Group Services ───────────────────────────────────────

async def test_group_set_on(rest):
    """group.set with state=on sets group to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.cusgs_gon_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("group", "set", {"entity_id": eid, "state": "on"})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_group_set_off(rest):
    """group.set with state=off sets group to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.cusgs_goff_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("group", "set", {"entity_id": eid, "state": "off"})
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_group_set_default_on(rest):
    """group.set without state field defaults to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"group.cusgs_gdef_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("group", "set", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── Weather Services ─────────────────────────────────────

async def test_weather_get_forecasts_noop(rest):
    """weather.get_forecasts is a no-op (read-only stub)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"weather.cusgs_wx_{tag}"
    await rest.set_state(eid, "sunny", {"temperature": 72})
    await rest.call_service("weather", "get_forecasts", {"entity_id": eid})
    # State should be unchanged (no-op)
    state = await rest.get_state(eid)
    assert state["state"] == "sunny"
    assert state["attributes"]["temperature"] == 72


# ── Device Tracker Services ──────────────────────────────

async def test_device_tracker_see_location(rest):
    """device_tracker.see sets location_name attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.cusgs_dt_{tag}"
    await rest.set_state(eid, "unknown")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "home",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["location_name"] == "home"


# ── Input Datetime Services ──────────────────────────────

async def test_input_datetime_set_datetime(rest):
    """input_datetime.set_datetime sets state to datetime string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.cusgs_idt_{tag}"
    await rest.set_state(eid, "2025-01-01 00:00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "datetime": "2025-06-15 14:30:00",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "2025-06-15 14:30:00"
