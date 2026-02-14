"""
CTS -- WS Service Domain Dispatch Depth Tests

Tests WS call_service dispatching across multiple domains: light,
switch, lock, climate, cover, fan. Verifies state changes via REST
after WS service calls, including data passthrough.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Light ─────────────────────────────────────────────────

async def test_ws_light_turn_on(ws, rest):
    """WS light/turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsd_on_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_light_turn_on_with_brightness(ws, rest):
    """WS light/turn_on with brightness passes through."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsd_br_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 128},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 128


async def test_ws_light_turn_off(ws, rest):
    """WS light/turn_off sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsd_off_{tag}"
    await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_off",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Switch ────────────────────────────────────────────────

async def test_ws_switch_turn_on(ws, rest):
    """WS switch/turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.wsd_on_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_switch_toggle(ws, rest):
    """WS switch/toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.wsd_tog_{tag}"
    await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Lock ──────────────────────────────────────────────────

async def test_ws_lock_lock(ws, rest):
    """WS lock/lock sets state to locked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.wsd_lock_{tag}"
    await rest.set_state(eid, "unlocked")

    await ws.send_command(
        "call_service",
        domain="lock",
        service="lock",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "locked"


async def test_ws_lock_unlock(ws, rest):
    """WS lock/unlock sets state to unlocked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.wsd_unlock_{tag}"
    await rest.set_state(eid, "locked")

    await ws.send_command(
        "call_service",
        domain="lock",
        service="unlock",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "unlocked"


# ── Climate ───────────────────────────────────────────────

async def test_ws_climate_set_hvac_mode(ws, rest):
    """WS climate/set_hvac_mode changes state to mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.wsd_hvac_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="climate",
        service="set_hvac_mode",
        service_data={"entity_id": eid, "hvac_mode": "cool"},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "cool"


async def test_ws_climate_set_temperature(ws, rest):
    """WS climate/set_temperature sets temperature attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.wsd_temp_{tag}"
    await rest.set_state(eid, "heat")

    await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid, "temperature": 72},
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


# ── Cover ─────────────────────────────────────────────────

async def test_ws_cover_open(ws, rest):
    """WS cover/open_cover sets state to open."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.wsd_open_{tag}"
    await rest.set_state(eid, "closed")

    await ws.send_command(
        "call_service",
        domain="cover",
        service="open_cover",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "open"


async def test_ws_cover_close(ws, rest):
    """WS cover/close_cover sets state to closed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.wsd_close_{tag}"
    await rest.set_state(eid, "open")

    await ws.send_command(
        "call_service",
        domain="cover",
        service="close_cover",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "closed"


# ── Fan ───────────────────────────────────────────────────

async def test_ws_fan_turn_on(ws, rest):
    """WS fan/turn_on sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.wsd_on_{tag}"
    await rest.set_state(eid, "off")

    await ws.send_command(
        "call_service",
        domain="fan",
        service="turn_on",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_ws_fan_set_percentage(ws, rest):
    """WS fan/set_percentage sets percentage attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.wsd_pct_{tag}"
    await rest.set_state(eid, "on")

    await ws.send_command(
        "call_service",
        domain="fan",
        service="set_percentage",
        service_data={"entity_id": eid, "percentage": 75},
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 75
