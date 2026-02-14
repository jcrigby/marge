"""
CTS -- WebSocket Service Dispatch Depth Tests

Tests WS call_service for various domains, entity_id as string vs array,
target.entity_id pattern, and multi-entity service calls.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic WS service dispatch ────────────────────────────

async def test_ws_call_light_turn_on(ws, rest):
    """WS call_service light.turn_on sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_lt_{tag}"
    await rest.set_state(eid, "off")
    resp = await ws.send_command("call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 200},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_ws_call_switch_toggle(ws, rest):
    """WS call_service switch.toggle flips state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_sw_{tag}"
    await rest.set_state(eid, "on")
    resp = await ws.send_command("call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ws_call_lock_lock(ws, rest):
    """WS call_service lock.lock sets state to locked."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ws_lk_{tag}"
    await rest.set_state(eid, "unlocked")
    resp = await ws.send_command("call_service",
        domain="lock",
        service="lock",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "locked"


# ── entity_id as array ───────────────────────────────────

async def test_ws_call_service_entity_array(ws, rest):
    """WS call_service with entity_id as array applies to all."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"light.ws_arr1_{tag}"
    eid2 = f"light.ws_arr2_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "off")
    resp = await ws.send_command("call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid1, eid2]},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid1))["state"] == "on"
    assert (await rest.get_state(eid2))["state"] == "on"


# ── target.entity_id pattern ─────────────────────────────

async def test_ws_call_service_target_entity(ws, rest):
    """WS call_service with target.entity_id pattern."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_tgt_{tag}"
    await rest.set_state(eid, "off")
    resp = await ws.send_command("call_service",
        domain="switch",
        service="turn_on",
        service_data={},
        target={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "on"


async def test_ws_call_service_target_entity_array(ws, rest):
    """WS call_service with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"switch.ws_tga1_{tag}"
    eid2 = f"switch.ws_tga2_{tag}"
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "on")
    resp = await ws.send_command("call_service",
        domain="switch",
        service="turn_off",
        service_data={},
        target={"entity_id": [eid1, eid2]},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid1))["state"] == "off"
    assert (await rest.get_state(eid2))["state"] == "off"


# ── Climate via WS ────────────────────────────────────────

async def test_ws_call_climate_set_temperature(ws, rest):
    """WS call_service climate.set_temperature sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ws_clim_{tag}"
    await rest.set_state(eid, "heat")
    resp = await ws.send_command("call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid, "temperature": 72},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


# ── Cover via WS ──────────────────────────────────────────

async def test_ws_call_cover_set_position(ws, rest):
    """WS call_service cover.set_cover_position sets position."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.ws_cvr_{tag}"
    await rest.set_state(eid, "closed")
    resp = await ws.send_command("call_service",
        domain="cover",
        service="set_cover_position",
        service_data={"entity_id": eid, "position": 50},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


# ── Fan via WS ────────────────────────────────────────────

async def test_ws_call_fan_set_percentage(ws, rest):
    """WS call_service fan.set_percentage sets percentage."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.ws_fn_{tag}"
    await rest.set_state(eid, "on")
    resp = await ws.send_command("call_service",
        domain="fan",
        service="set_percentage",
        service_data={"entity_id": eid, "percentage": 75},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["percentage"] == 75


# ── Media Player via WS ──────────────────────────────────

async def test_ws_call_media_player_volume(ws, rest):
    """WS call_service media_player.volume_set works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"media_player.ws_mp_{tag}"
    await rest.set_state(eid, "playing")
    resp = await ws.send_command("call_service",
        domain="media_player",
        service="volume_set",
        service_data={"entity_id": eid, "volume_level": 0.6},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["volume_level"] == 0.6


# ── Counter via WS ────────────────────────────────────────

async def test_ws_call_counter_increment(ws, rest):
    """WS call_service counter.increment increases value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ws_ctr_{tag}"
    await rest.set_state(eid, "10")
    resp = await ws.send_command("call_service",
        domain="counter",
        service="increment",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "11"
