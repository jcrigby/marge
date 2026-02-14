"""
CTS -- WebSocket Connection Lifecycle Depth Tests

Tests WebSocket auth flow (auth_required → auth → auth_ok),
connection lifecycle, subscription management, concurrent
subscribers, and protocol edge cases.
"""

import asyncio
import json
import uuid
import pytest
import websockets

BASE_WS = "ws://localhost:8124/api/websocket"

pytestmark = pytest.mark.asyncio


async def ws_connect_and_auth(token=""):
    """Helper: connect to WS, receive auth_required, send auth, return socket."""
    ws = await websockets.connect(BASE_WS)
    # Receive auth_required
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_required"
    # Send auth
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    # Receive auth_ok
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_ok"
    return ws


async def test_auth_required_on_connect():
    """Server sends auth_required as first message."""
    ws = await websockets.connect(BASE_WS)
    msg = json.loads(await ws.recv())
    assert msg["type"] == "auth_required"
    assert "ha_version" in msg
    await ws.close()


async def test_auth_ok_with_empty_token():
    """Auth succeeds with empty token (open mode)."""
    ws = await ws_connect_and_auth("")
    await ws.close()


async def test_auth_ok_with_arbitrary_token():
    """Auth succeeds with any token in open mode."""
    ws = await ws_connect_and_auth("any-token-works")
    await ws.close()


async def test_ha_version_in_auth_messages():
    """Both auth_required and auth_ok contain ha_version."""
    ws = await websockets.connect(BASE_WS)
    req = json.loads(await ws.recv())
    assert "ha_version" in req
    version = req["ha_version"]
    assert len(version) > 0

    await ws.send(json.dumps({"type": "auth", "access_token": ""}))
    ok = json.loads(await ws.recv())
    assert "ha_version" in ok
    assert ok["ha_version"] == version
    await ws.close()


async def test_command_after_auth():
    """Commands work after successful auth."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({"id": 1, "type": "ping"}))
    msg = json.loads(await ws.recv())
    assert msg["id"] == 1
    assert msg["type"] == "pong"
    await ws.close()


async def test_subscribe_returns_success():
    """subscribe_events returns success result."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({
        "id": 1, "type": "subscribe_events", "event_type": "state_changed",
    }))
    msg = json.loads(await ws.recv())
    assert msg["id"] == 1
    assert msg["success"] is True
    await ws.close()


async def test_unsubscribe_returns_success():
    """unsubscribe_events returns success."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({
        "id": 1, "type": "subscribe_events", "event_type": "state_changed",
    }))
    await ws.recv()  # subscribe result

    await ws.send(json.dumps({
        "id": 2, "type": "unsubscribe_events", "subscription": 1,
    }))
    msg = json.loads(await ws.recv())
    assert msg["id"] == 2
    assert msg["success"] is True
    await ws.close()


async def test_multiple_subscriptions():
    """Multiple subscribe_events are tracked independently."""
    ws = await ws_connect_and_auth()

    for i in range(1, 4):
        await ws.send(json.dumps({
            "id": i, "type": "subscribe_events", "event_type": "state_changed",
        }))
        msg = json.loads(await ws.recv())
        assert msg["id"] == i
        assert msg["success"] is True

    await ws.close()


async def test_concurrent_ws_connections(rest):
    """Multiple WebSocket connections work concurrently."""
    sockets = []
    for _ in range(3):
        ws = await ws_connect_and_auth()
        sockets.append(ws)

    # All can send commands
    for i, ws in enumerate(sockets):
        await ws.send(json.dumps({"id": 1, "type": "ping"}))
        msg = json.loads(await ws.recv())
        assert msg["type"] == "pong"

    for ws in sockets:
        await ws.close()


async def test_unknown_command_returns_error():
    """Unknown command type returns error result."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({"id": 1, "type": "totally_bogus_command"}))
    msg = json.loads(await ws.recv())
    assert msg["id"] == 1
    assert msg["success"] is False
    await ws.close()


async def test_get_config_returns_location():
    """get_config returns location_name and coordinates."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({"id": 1, "type": "get_config"}))
    msg = json.loads(await ws.recv())
    assert msg["success"] is True
    result = msg["result"]
    assert "location_name" in result
    assert "latitude" in result
    assert "longitude" in result
    assert "time_zone" in result
    assert "version" in result
    assert "state" in result
    assert result["state"] == "RUNNING"
    await ws.close()


async def test_get_services_format():
    """get_services returns list of {domain, services}."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({"id": 1, "type": "get_services"}))
    msg = json.loads(await ws.recv())
    assert msg["success"] is True
    result = msg["result"]
    assert isinstance(result, list)
    domains = [entry["domain"] for entry in result]
    assert "light" in domains
    assert "switch" in domains
    await ws.close()


async def test_render_template_via_ws():
    """render_template returns rendered string."""
    ws = await ws_connect_and_auth()
    await ws.send(json.dumps({
        "id": 1, "type": "render_template",
        "template": "{{ 2 + 3 }}",
    }))
    msg = json.loads(await ws.recv())
    assert msg["success"] is True
    assert msg["result"]["result"] == "5"
    await ws.close()


async def test_sequential_ids_tracked():
    """Response IDs match request IDs in order."""
    ws = await ws_connect_and_auth()
    for i in [10, 20, 30]:
        await ws.send(json.dumps({"id": i, "type": "ping"}))
        msg = json.loads(await ws.recv())
        assert msg["id"] == i
    await ws.close()
