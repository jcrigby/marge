"""
CTS -- WebSocket Service Call Dispatch Tests

Tests WebSocket service call paths: target entity patterns,
entity arrays, missing entities, and cross-domain dispatch.
"""

import asyncio
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
    await rest.set_state("light.ws_svc_arr1", "off")
    await rest.set_state("light.ws_svc_arr2", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": ["light.ws_svc_arr1", "light.ws_svc_arr2"]},
    )
    assert resp["success"] is True
    s1 = await rest.get_state("light.ws_svc_arr1")
    s2 = await rest.get_state("light.ws_svc_arr2")
    assert s1["state"] == "on"
    assert s2["state"] == "on"


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
    await rest.set_state("switch.ws_svc_tog", "on")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        target={"entity_id": "switch.ws_svc_tog"},
    )
    assert resp["success"] is True
    state = await rest.get_state("switch.ws_svc_tog")
    assert state["state"] == "off"


async def test_ws_call_service_climate(ws, rest):
    """WS call_service for climate domain works."""
    await rest.set_state("climate.ws_svc_clim", "off")
    resp = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        target={"entity_id": "climate.ws_svc_clim"},
        service_data={"temperature": 72},
    )
    assert resp["success"] is True
    state = await rest.get_state("climate.ws_svc_clim")
    assert state["attributes"].get("temperature") == 72


async def test_ws_call_service_lock(ws, rest):
    """WS call_service for lock domain works."""
    await rest.set_state("lock.ws_svc_lock", "unlocked")
    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="lock",
        target={"entity_id": "lock.ws_svc_lock"},
    )
    assert resp["success"] is True
    state = await rest.get_state("lock.ws_svc_lock")
    assert state["state"] == "locked"


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
