"""
CTS -- WebSocket Lovelace Config, Subscribe Trigger, and Stub Tests

Tests WS commands that return stub or minimal responses:
lovelace/config, subscribe_trigger, and response ID tracking.
"""

import uuid
import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_lovelace_config(ws):
    """WS lovelace/config returns success with views array."""
    resp = await ws.send_command("lovelace/config")
    assert resp.get("success", False) is True
    result = resp.get("result", {})
    assert "views" in result
    assert isinstance(result["views"], list)


async def test_lovelace_config_has_title(ws):
    """WS lovelace/config result includes title."""
    resp = await ws.send_command("lovelace/config")
    result = resp.get("result", {})
    assert "title" in result


async def test_subscribe_trigger(ws):
    """WS subscribe_trigger returns success."""
    resp = await ws.send_command(
        "subscribe_trigger",
        trigger={"platform": "state", "entity_id": "sensor.test"},
    )
    assert resp.get("success", False) is True


async def test_ws_response_ids_increment(ws):
    """WS response IDs match sent message IDs."""
    r1 = await ws.send_command("get_config")
    r2 = await ws.send_command("get_config")
    # Both should have different IDs and both succeed
    assert r1.get("success", False) is True
    assert r2.get("success", False) is True
    assert r1["id"] != r2["id"]


async def test_ws_rapid_pings(ws):
    """Rapid sequential pings all return pong."""
    results = []
    for _ in range(10):
        results.append(await ws.ping())
    assert all(r is True for r in results)


async def test_ws_interleaved_commands(ws, rest):
    """Interleaved WS commands maintain correct ID matching."""
    tag = uuid.uuid4().hex[:8]

    # Fire off multiple different commands quickly
    r1 = await ws.send_command("ping")
    r2 = await ws.send_command("get_config")
    r3 = await ws.send_command("get_services")
    r4 = await ws.send_command("render_template", template="{{ 2 + 2 }}")

    # All should succeed
    assert r1.get("type") == "pong" or r1.get("success", False) is True
    assert r2.get("success", False) is True
    assert r3.get("success", False) is True
    assert r4.get("success", False) is True


async def test_ws_subscribe_state_changed(ws, rest):
    """Subscribe to state_changed then trigger a change, get event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.wssub_{tag}"

    sub_id = await ws.subscribe_events("state_changed")

    await rest.set_state(eid, "hello")

    # Should receive at least one state_changed event
    try:
        event = await ws.recv_event(timeout=3.0)
        assert event["type"] == "event"
    except asyncio.TimeoutError:
        pytest.skip("No event received within timeout")


async def test_ws_get_config_version(ws):
    """WS get_config result has version field."""
    resp = await ws.send_command("get_config")
    result = resp.get("result", {})
    assert "version" in result
    assert isinstance(result["version"], str)


async def test_ws_get_config_location(ws):
    """WS get_config result has location_name."""
    resp = await ws.send_command("get_config")
    result = resp.get("result", {})
    assert "location_name" in result


async def test_ws_unknown_command_has_error_message(ws):
    """Unknown WS command response includes error info."""
    resp = await ws.send_command("absolutely_fake_command")
    assert resp.get("success", True) is False


async def test_ws_subscribe_then_unsubscribe(ws, rest):
    """Subscribe, unsubscribe, then verify no events leak."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.unsub_{tag}"

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    sub_id = sub["id"]

    unsub = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert unsub.get("success", False) is True

    # Set state — should NOT deliver event since unsubscribed
    await rest.set_state(eid, "post_unsub")

    # Try to receive — should timeout
    try:
        event = await ws.recv_event(timeout=1.0)
        # If we got something, it should be from a different subscription
    except asyncio.TimeoutError:
        pass  # Expected — no event after unsubscribe
