"""
CTS -- Concurrent WebSocket Clients Depth Tests

Tests multiple WebSocket connections: all receive state_changed events,
independent subscriptions, WS commands don't interfere, and connection
isolation.
"""

import asyncio
import json
import uuid
import pytest
import websockets

pytestmark = pytest.mark.asyncio

WS_URL = "ws://localhost:8124/api/websocket"


async def _connect_ws():
    """Connect a raw websocket and complete auth handshake."""
    ws = await websockets.connect(WS_URL, max_size=2**22)
    auth_req = json.loads(await ws.recv())
    assert auth_req["type"] == "auth_required"
    await ws.send(json.dumps({"type": "auth", "access_token": "test-token"}))
    auth_ok = json.loads(await ws.recv())
    assert auth_ok["type"] == "auth_ok"
    return ws


async def _subscribe(ws, msg_id=1):
    """Subscribe to state_changed events."""
    await ws.send(json.dumps({
        "id": msg_id,
        "type": "subscribe_events",
        "event_type": "state_changed",
    }))
    resp = json.loads(await ws.recv())
    assert resp.get("success") is True
    return msg_id


async def _recv_event(ws, timeout=3.0):
    """Receive next WS event."""
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


# ── Multiple Clients Receive Events ──────────────────────

async def test_two_clients_both_receive_event(rest):
    """Two WS clients both receive the same state_changed event."""
    ws1 = await _connect_ws()
    ws2 = await _connect_ws()
    try:
        await _subscribe(ws1, 10)
        await _subscribe(ws2, 20)

        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.cws_both_{tag}"
        await rest.set_state(eid, "42")

        ev1 = await _recv_event(ws1)
        ev2 = await _recv_event(ws2)

        assert ev1["event"]["data"]["entity_id"] == eid
        assert ev2["event"]["data"]["entity_id"] == eid
    finally:
        await ws1.close()
        await ws2.close()


# ── Unsubscribe Stops Events ────────────────────────────

async def test_unsubscribe_stops_events(rest):
    """After unsubscribe, client no longer receives events."""
    ws = await _connect_ws()
    try:
        sub_id = await _subscribe(ws, 10)
        # Unsubscribe
        await ws.send(json.dumps({
            "id": 11,
            "type": "unsubscribe_events",
            "subscription": sub_id,
        }))
        unsub_resp = json.loads(await ws.recv())
        assert unsub_resp.get("success") is True

        tag = uuid.uuid4().hex[:8]
        await rest.set_state(f"sensor.cws_unsub_{tag}", "99")

        # Should NOT receive event (timeout expected)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(ws.recv(), timeout=0.5)
    finally:
        await ws.close()


# ── Independent Commands ─────────────────────────────────

async def test_independent_commands(rest):
    """Commands on one client don't affect another."""
    ws1 = await _connect_ws()
    ws2 = await _connect_ws()
    try:
        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.cws_ind_{tag}"
        await rest.set_state(eid, "42")

        # Both clients can read states independently
        await ws1.send(json.dumps({"id": 1, "type": "get_config"}))
        r1 = json.loads(await ws1.recv())
        assert r1.get("success") is True

        await ws2.send(json.dumps({"id": 1, "type": "get_config"}))
        r2 = json.loads(await ws2.recv())
        assert r2.get("success") is True

        # Results should match
        assert r1["result"]["version"] == r2["result"]["version"]
    finally:
        await ws1.close()
        await ws2.close()


# ── Ping Pong ────────────────────────────────────────────

async def test_ping_pong_independent(rest):
    """Ping on one client returns pong only to that client."""
    ws1 = await _connect_ws()
    ws2 = await _connect_ws()
    try:
        await ws1.send(json.dumps({"id": 99, "type": "ping"}))
        pong = json.loads(await ws1.recv())
        assert pong["type"] == "pong"
        assert pong["id"] == 99

        # ws2 should not have received anything
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(ws2.recv(), timeout=0.3)
    finally:
        await ws1.close()
        await ws2.close()


# ── Close One, Other Survives ────────────────────────────

async def test_close_one_other_survives(rest):
    """Closing one WS connection doesn't affect another."""
    ws1 = await _connect_ws()
    ws2 = await _connect_ws()
    try:
        await _subscribe(ws2, 20)
        await ws1.close()
        ws1 = None

        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.cws_surv_{tag}"
        await rest.set_state(eid, "alive")

        ev = await _recv_event(ws2)
        assert ev["event"]["data"]["entity_id"] == eid
    finally:
        if ws1:
            await ws1.close()
        await ws2.close()


# ── Multiple Subscriptions Same Client ───────────────────

async def test_multiple_subscriptions_one_client(rest):
    """Multiple subscribe_events on same client produce events for each."""
    ws = await _connect_ws()
    try:
        await _subscribe(ws, 10)
        await _subscribe(ws, 20)

        tag = uuid.uuid4().hex[:8]
        eid = f"sensor.cws_multi_{tag}"
        await rest.set_state(eid, "42")

        # Should receive 2 events (one per subscription)
        ev1 = await _recv_event(ws)
        ev2 = await _recv_event(ws)
        ids = {ev1.get("id"), ev2.get("id")}
        assert 10 in ids
        assert 20 in ids
    finally:
        await ws.close()


# ── WS Connection Count in Health ────────────────────────

async def test_ws_connections_counted(rest):
    """Health endpoint reflects active WS connection count."""
    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    base_count = h1["ws_connections"]

    ws = await _connect_ws()
    try:
        await asyncio.sleep(0.1)
        h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
        assert h2["ws_connections"] >= base_count + 1
    finally:
        await ws.close()
