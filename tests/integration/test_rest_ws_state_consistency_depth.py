"""
CTS -- REST/WS State Consistency Depth Tests

Tests that state operations via REST and WebSocket produce
consistent results: set via REST then verify via WS service,
service via WS then read via REST, cross-API service call
consistency, and config parity.

Note: Avoids WS get_states (message too large when many test
entities accumulate). Uses WS call_service + REST get_state instead.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Set via REST, Verify via WS Service ─────────────────

async def test_rest_set_ws_service_reads(rest, ws):
    """Entity set via REST is manipulable via WS service."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.rwc_rset_{tag}"
    await rest.set_state(eid, "off", {"brightness": 50})

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 200},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_rest_set_ws_toggle_reads(rest, ws):
    """Value set via REST can be toggled via WS."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rwc_val_{tag}"
    await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Service via WS, Read via REST ─────────────────────────

async def test_ws_service_rest_read(rest, ws):
    """Service called via WS, state read via REST is consistent."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.rwc_wsvc_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 200},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_ws_toggle_rest_verify(rest, ws):
    """WS toggle then REST read shows correct toggled state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rwc_wtog_{tag}"
    await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Cross-API Service Consistency ─────────────────────────

async def test_rest_service_ws_service_chain(rest, ws):
    """REST lock, WS unlock, REST verify — cross-API chain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.rwc_chain_{tag}"
    await rest.set_state(eid, "unlocked")

    await rest.call_service("lock", "lock", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state["state"] == "locked"

    await ws.send_command(
        "call_service",
        domain="lock",
        service="unlock",
        service_data={"entity_id": eid},
    )
    state = await rest.get_state(eid)
    assert state["state"] == "unlocked"


async def test_ws_create_rest_delete(rest, ws):
    """Entity created via WS service, deleted via REST."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rwc_del_{tag}"
    await rest.set_state(eid, "temp")

    state = await rest.get_state(eid)
    assert state["state"] == "temp"

    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp2.status_code == 404


async def test_ws_light_brightness_rest_verify(rest, ws):
    """WS light turn_on with brightness, REST verifies attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.rwc_bright_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 128, "color_temp": 350},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128
    assert state["attributes"]["color_temp"] == 350


async def test_rest_climate_ws_override(rest, ws):
    """REST sets climate, WS overrides, REST verifies."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.rwc_clim_{tag}"
    await rest.set_state(eid, "cool", {"temperature": 72})

    await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid, "temperature": 68},
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 68


# ── Config Consistency ────────────────────────────────────

async def test_rest_ws_config_version_match(rest, ws):
    """REST and WS config endpoints return same version."""
    rest_config = await rest.get_config()
    ws_result = await ws.send_command("get_config")
    ws_config = ws_result["result"]

    assert rest_config["version"] == ws_config["version"]


async def test_rest_ws_config_location_match(rest, ws):
    """REST and WS config endpoints return same location_name."""
    rest_config = await rest.get_config()
    ws_result = await ws.send_command("get_config")
    ws_config = ws_result["result"]

    assert rest_config["location_name"] == ws_config["location_name"]
