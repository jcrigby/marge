"""
CTS -- WebSocket Service Call Dispatch Tests

Tests WebSocket service call paths: target entity patterns,
entity arrays, missing entities, and cross-domain dispatch.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_ws_call_service_with_target(ws, rest):
    """WS call_service with target.entity_id works."""
    await rest.set_state("light.ws_svc_t1", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": "light.ws_svc_t1"},
    )
    assert resp["success"] is True


async def test_ws_call_service_with_service_data(ws, rest):
    """WS call_service with service_data.entity_id works."""
    await rest.set_state("switch.ws_svc_d1", "off")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": "switch.ws_svc_d1"},
    )
    assert resp["success"] is True
    state = await rest.get_state("switch.ws_svc_d1")
    assert state["state"] == "on"


async def test_ws_call_service_entity_array(ws, rest):
    """WS call_service with array of entity_ids."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"light.ws_arr1_{tag}"
    eid2 = f"light.ws_arr2_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid1, eid2]},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid1))["state"] == "on"
    assert (await rest.get_state(eid2))["state"] == "on"


async def test_ws_call_service_with_data(ws, rest):
    """WS call_service passes data to service handler."""
    await rest.set_state("light.ws_svc_data", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": "light.ws_svc_data"},
        service_data={"brightness": 128},
    )
    assert resp["success"] is True
    state = await rest.get_state("light.ws_svc_data")
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 128


async def test_ws_call_service_toggle(ws, rest):
    """WS call_service toggle switches state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_sw_{tag}"
    await rest.set_state(eid, "on")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ws_call_service_climate(ws, rest):
    """WS call_service for climate domain works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ws_clim_{tag}"
    await rest.set_state(eid, "heat")
    resp = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid, "temperature": 72},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


async def test_ws_call_service_lock(ws, rest):
    """WS call_service for lock domain works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ws_lk_{tag}"
    await rest.set_state(eid, "unlocked")
    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="lock",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "locked"


async def test_ws_call_service_scene(ws, rest):
    """WS call_service activating a scene works."""
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        target={"entity_id": "scene.evening"},
    )
    assert resp["success"] is True


async def test_ws_fire_event(ws):
    """WS fire_event command works."""
    resp = await ws.send_command(
        "fire_event",
        event_type="test_ws_fire",
        event_data={"key": "value"},
    )
    assert resp["success"] is True


async def test_ws_get_services(ws):
    """WS get_services returns service registry."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    assert "result" in resp
    result = resp["result"]
    assert isinstance(result, list)
    domains = [s["domain"] for s in result]
    assert "light" in domains
    assert "switch" in domains


async def test_ws_get_config(ws):
    """WS get_config returns config object."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    result = resp["result"]
    assert "latitude" in result
    assert "longitude" in result
    assert "state" in result


# ── Merged from test_ws_service_dispatch_depth.py ────────


async def test_ws_call_service_light_with_brightness(ws, rest):
    """WS call_service light.turn_on with brightness sets attribute."""
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


@pytest.mark.parametrize("domain,service,entity_prefix,initial_state,service_data_extra,expected_attr,expected_attr_val", [
    ("cover", "set_cover_position", "cover.ws_cvr", "closed", {"position": 50}, "current_position", 50),
    ("fan", "set_percentage", "fan.ws_fn", "on", {"percentage": 75}, "percentage", 75),
    ("media_player", "volume_set", "media_player.ws_mp", "playing", {"volume_level": 0.6}, "volume_level", 0.6),
], ids=["cover-position", "fan-percentage", "media-player-volume"])
async def test_ws_call_service_attribute_domains(ws, rest, domain, service, entity_prefix, initial_state, service_data_extra, expected_attr, expected_attr_val):
    """WS call_service for various domains sets expected attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"{entity_prefix}_{tag}"
    await rest.set_state(eid, initial_state)
    svc_data = {"entity_id": eid, **service_data_extra}
    resp = await ws.send_command("call_service",
        domain=domain,
        service=service,
        service_data=svc_data,
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"][expected_attr] == expected_attr_val


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
