"""
CTS -- Humidifier, Camera Motion Detection, and Device Tracker Depth Tests

Tests humidifier services (turn_on/off/toggle, set_humidity, set_mode),
camera motion detection (enable/disable_motion_detection),
device_tracker.see with location_name and GPS attributes.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Humidifier On/Off/Toggle ─────────────────────────────

async def test_humidifier_turn_on(rest):
    """humidifier.turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


async def test_humidifier_turn_off(rest):
    """humidifier.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_off_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "turn_off", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_toggle_on_to_off(rest):
    """humidifier.toggle: on → off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_tog1_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


async def test_humidifier_toggle_off_to_on(rest):
    """humidifier.toggle: off → on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_tog2_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"


# ── Humidifier set_humidity ───────────────────────────────

async def test_humidifier_set_humidity(rest):
    """humidifier.set_humidity sets humidity attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_hum_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 55,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["humidity"] == 55
    assert state["state"] == "on"


async def test_humidifier_set_humidity_preserves_attrs(rest):
    """set_humidity preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_hpa_{tag}"
    await rest.set_state(eid, "on", {"friendly_name": "Bedroom Humidifier", "mode": "auto"})
    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 60,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["humidity"] == 60
    assert state["attributes"]["friendly_name"] == "Bedroom Humidifier"
    assert state["attributes"]["mode"] == "auto"


# ── Humidifier set_mode ───────────────────────────────────

async def test_humidifier_set_mode(rest):
    """humidifier.set_mode sets mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_mode_{tag}"
    await rest.set_state(eid, "on")
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "eco",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["mode"] == "eco"


async def test_humidifier_set_mode_sleep(rest):
    """humidifier.set_mode to sleep preserves state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_ms_{tag}"
    await rest.set_state(eid, "on", {"humidity": 50})
    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "sleep",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["mode"] == "sleep"
    assert state["attributes"]["humidity"] == 50


# ── Humidifier full lifecycle ─────────────────────────────

async def test_humidifier_lifecycle(rest):
    """Humidifier: off → on → set_humidity → set_mode → toggle off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"humidifier.hum_life_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("humidifier", "turn_on", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "on"

    await rest.call_service("humidifier", "set_humidity", {
        "entity_id": eid, "humidity": 45,
    })
    assert (await rest.get_state(eid))["attributes"]["humidity"] == 45

    await rest.call_service("humidifier", "set_mode", {
        "entity_id": eid, "mode": "normal",
    })
    assert (await rest.get_state(eid))["attributes"]["mode"] == "normal"

    await rest.call_service("humidifier", "toggle", {"entity_id": eid})
    assert (await rest.get_state(eid))["state"] == "off"


# ── Camera Motion Detection ──────────────────────────────

async def test_camera_enable_motion_detection(rest):
    """camera.enable_motion_detection sets motion_detection attribute to true."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cam_md_{tag}"
    await rest.set_state(eid, "idle")
    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is True
    assert state["state"] == "idle"


async def test_camera_disable_motion_detection(rest):
    """camera.disable_motion_detection sets motion_detection attribute to false."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cam_dmd_{tag}"
    await rest.set_state(eid, "streaming", {"motion_detection": True})
    await rest.call_service("camera", "disable_motion_detection", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["attributes"]["motion_detection"] is False
    assert state["state"] == "streaming"


async def test_camera_motion_toggle_cycle(rest):
    """Camera motion detection: enable → disable → enable."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.cam_mtog_{tag}"
    await rest.set_state(eid, "idle")

    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    assert (await rest.get_state(eid))["attributes"]["motion_detection"] is True

    await rest.call_service("camera", "disable_motion_detection", {"entity_id": eid})
    assert (await rest.get_state(eid))["attributes"]["motion_detection"] is False

    await rest.call_service("camera", "enable_motion_detection", {"entity_id": eid})
    assert (await rest.get_state(eid))["attributes"]["motion_detection"] is True


# ── Device Tracker ────────────────────────────────────────

async def test_device_tracker_see_location(rest):
    """device_tracker.see sets state to location_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dt_{tag}"
    await rest.set_state(eid, "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid, "location_name": "work",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "work"
    assert state["attributes"]["location_name"] == "work"


async def test_device_tracker_see_gps(rest):
    """device_tracker.see sets gps attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dt_gps_{tag}"
    await rest.set_state(eid, "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "office",
        "gps": [37.7749, -122.4194],
    })
    state = await rest.get_state(eid)
    assert state["state"] == "office"
    assert state["attributes"]["gps"] == [37.7749, -122.4194]


async def test_device_tracker_see_default_home(rest):
    """device_tracker.see without location_name defaults to home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dt_def_{tag}"
    await rest.set_state(eid, "not_home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
    })
    state = await rest.get_state(eid)
    assert state["state"] == "home"
