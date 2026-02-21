"""
CTS -- Cross-API Integration Tests

Tests that state changes propagate correctly across REST, WebSocket,
and service call interfaces. Verifies consistency between different
API access methods.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_rest_set_ws_read(rest, ws):
    """State set via REST is readable via WS get_states."""
    await rest.set_state("sensor.cross_rw", "42")
    resp = await ws.send_command("get_states")
    states = resp["result"]
    found = [s for s in states if s["entity_id"] == "sensor.cross_rw"]
    assert len(found) == 1
    assert found[0]["state"] == "42"


async def test_ws_service_rest_read(ws, rest):
    """State changed via WS service call readable via REST."""
    await rest.set_state("light.cross_wr", "off")
    await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": "light.cross_wr"},
    )
    state = await rest.get_state("light.cross_wr")
    assert state["state"] == "on"


async def test_rest_service_ws_event(ws, rest):
    """REST service call triggers WS state_changed event."""
    sub = await ws.send_command("subscribe_events")
    assert sub["success"] is True

    await rest.set_state("sensor.cross_evt", "before")
    # Should get a state_changed event
    event = await ws.recv_event(timeout=2.0)
    assert event is not None


async def test_scene_via_rest_ws_verify(rest, ws):
    """Scene activated via REST, verify entity states via WS."""
    # Activate evening scene via REST
    await rest.call_service("scene", "turn_on", {"entity_id": "scene.evening"})

    # Verify via WS get_states
    resp = await ws.send_command("get_states")
    states = {s["entity_id"]: s for s in resp["result"]}
    if "light.living_room_main" in states:
        assert states["light.living_room_main"]["state"] == "on"


async def test_config_consistent_rest_ws(rest, ws):
    """Config endpoint returns same data via REST and WS."""
    rest_config = await rest.get_config()
    ws_resp = await ws.send_command("get_config")
    ws_config = ws_resp["result"]

    assert rest_config["location_name"] == ws_config["location_name"]
    assert rest_config["version"] == ws_config["version"]
    assert rest_config["latitude"] == ws_config["latitude"]


async def test_services_consistent_rest_ws(rest, ws):
    """Service listing consistent between REST and WS."""
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    rest_data = rest_resp.json()

    ws_resp = await ws.send_command("get_services")
    ws_data = ws_resp["result"]

    rest_domains = sorted([e["domain"] for e in rest_data])
    ws_domains = sorted([e["domain"] for e in ws_data])
    assert rest_domains == ws_domains


async def test_delete_via_rest_invisible_ws(rest, ws):
    """Deleted entity via REST not in WS get_states."""
    await rest.set_state("sensor.cross_del", "temp")
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.cross_del",
        headers=rest._headers(),
    )

    resp = await ws.send_command("get_states")
    ids = [s["entity_id"] for s in resp["result"]]
    assert "sensor.cross_del" not in ids


@pytest.mark.marge_only
async def test_health_ws_connections_accurate(rest, ws):
    """Health endpoint reflects at least 1 WS connection."""
    health = await rest.get_health()
    assert health["ws_connections"] >= 1
