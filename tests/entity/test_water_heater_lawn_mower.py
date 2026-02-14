"""
CTS -- Water Heater & Lawn Mower Domain Service Tests

Tests service calls for less-common domains: water_heater
(set_temperature, set_operation_mode) and lawn_mower (start/dock/pause).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_water_heater_set_temperature(rest):
    """water_heater.set_temperature stores temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.tank_{tag}"
    await rest.set_state(eid, "eco")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/water_heater/set_temperature",
        json={"entity_id": eid, "temperature": 120},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 120


async def test_water_heater_set_operation_mode(rest):
    """water_heater.set_operation_mode changes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.mode_{tag}"
    await rest.set_state(eid, "eco")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/water_heater/set_operation_mode",
        json={"entity_id": eid, "operation_mode": "performance"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "performance"


async def test_water_heater_turn_on(rest):
    """water_heater.turn_on sets state to eco (default operation mode)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.on_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/water_heater/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "eco"


async def test_water_heater_turn_off(rest):
    """water_heater.turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"water_heater.off_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/water_heater/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_lawn_mower_start(rest):
    """lawn_mower.start_mowing sets state to mowing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.garden_{tag}"
    await rest.set_state(eid, "docked")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/lawn_mower/start_mowing",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "mowing"


async def test_lawn_mower_dock(rest):
    """lawn_mower.dock sets state to docked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.dock_{tag}"
    await rest.set_state(eid, "mowing")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/lawn_mower/dock",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "docked"


async def test_lawn_mower_pause(rest):
    """lawn_mower.pause sets state to paused."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lawn_mower.pause_{tag}"
    await rest.set_state(eid, "mowing")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/lawn_mower/pause",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "paused"


async def test_remote_send_command(rest):
    """remote.send_command stores last_command attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"remote.tv_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/remote/send_command",
        json={"entity_id": eid, "command": "volume_up"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["last_command"] == "volume_up"


async def test_device_tracker_see(rest):
    """device_tracker.see sets state to location."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.phone_{tag}"
    await rest.set_state(eid, "not_home")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/device_tracker/see",
        json={"entity_id": eid, "location_name": "office"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "office"


async def test_update_install(rest):
    """update.install changes state to installing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"update.firmware_{tag}"
    await rest.set_state(eid, "available")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/update/install",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "installing"


async def test_camera_turn_on(rest):
    """camera.turn_on sets state to streaming."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.front_{tag}"
    await rest.set_state(eid, "idle")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/camera/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "streaming"


async def test_camera_turn_off(rest):
    """camera.turn_off sets state to idle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"camera.off_{tag}"
    await rest.set_state(eid, "streaming")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/camera/turn_off",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "idle"
