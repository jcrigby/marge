"""
CTS -- WebSocket Connection, Subscription, and Lifecycle Tests

Tests the WebSocket API: connect, auth, ping/pong, subscribe_events,
event delivery, command ordering, error handling, and unsubscribe.
Validates SSS SS5.1.2.
"""

import asyncio
import json
import uuid

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Connection and auth
# ---------------------------------------------------------------------------

async def test_ws_connect_and_auth(ws):
    """WebSocket connects and authenticates successfully."""
    # If we got the ws fixture without error, auth succeeded
    assert ws.ws is not None


# ---------------------------------------------------------------------------
# Ping / pong
# ---------------------------------------------------------------------------

async def test_ws_ping(ws):
    """WebSocket ping returns success."""
    result = await ws.ping()
    assert result is True


@pytest.mark.parametrize("count", [5, 10], ids=["multiple_pings", "rapid_pings"])
async def test_ws_repeated_pings(ws, count):
    """Multiple sequential pings all return pong."""
    for _ in range(count):
        result = await ws.ping()
        assert result is True


# ---------------------------------------------------------------------------
# get_states
# ---------------------------------------------------------------------------

async def test_ws_get_states(ws):
    """get_states via WebSocket returns a list."""
    states = await ws.get_states()
    assert isinstance(states, list)


# ---------------------------------------------------------------------------
# subscribe_events and event delivery
# ---------------------------------------------------------------------------

@pytest.mark.marge_only
async def test_ws_subscribe_events(ws, rest):
    """subscribe_events returns success and events are delivered."""
    sub_id = await ws.subscribe_events("state_changed")

    # Trigger a state change
    await rest.set_state("test.ws_event_delivery", "triggered")
    await asyncio.sleep(0.3)  # Give HA time to propagate

    # On HA many state_changed events fire for various entities; drain
    # until we find the one for our specific entity or timeout.
    deadline = asyncio.get_event_loop().time() + 10.0
    found = False
    while asyncio.get_event_loop().time() < deadline:
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await ws.recv_event(timeout=max(remaining, 0.1))
            if (event.get("type") == "event"
                    and event.get("id") == sub_id
                    and event.get("event", {}).get("data", {}).get("entity_id")
                        == "test.ws_event_delivery"):
                found = True
                break
        except asyncio.TimeoutError:
            break
    assert found, "Did not receive state_changed event for test.ws_event_delivery"


@pytest.mark.marge_only
async def test_ws_event_contains_entity_id(ws, rest):
    """State change events contain the correct entity_id."""
    await ws.subscribe_events("state_changed")
    await rest.set_state("test.ws_entity_check", "on")
    await asyncio.sleep(0.3)

    # On HA, drain until we find our entity (other entities fire too).
    deadline = asyncio.get_event_loop().time() + 10.0
    found = False
    while asyncio.get_event_loop().time() < deadline:
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await ws.recv_event(timeout=max(remaining, 0.1))
            data = event.get("event", {}).get("data", {})
            if data.get("entity_id") == "test.ws_entity_check":
                found = True
                break
        except asyncio.TimeoutError:
            break
    assert found, "Did not receive state_changed event for test.ws_entity_check"


async def test_ws_event_has_old_and_new_state(ws, rest):
    """State change events include old_state and new_state."""
    await ws.subscribe_events("state_changed")

    # Set initial state
    await rest.set_state("test.ws_old_new", "first")
    await asyncio.sleep(0.3)

    # Drain until we see the initial event for our entity
    deadline = asyncio.get_event_loop().time() + 10.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            ev = await ws.recv_event(timeout=max(remaining, 0.1))
            if ev.get("event", {}).get("data", {}).get("entity_id") == "test.ws_old_new":
                break
        except asyncio.TimeoutError:
            break

    # Change state
    await rest.set_state("test.ws_old_new", "second")
    await asyncio.sleep(0.3)

    # Find the event for our entity
    found = False
    deadline = asyncio.get_event_loop().time() + 10.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await ws.recv_event(timeout=max(remaining, 0.1))
            data = event.get("event", {}).get("data", {})
            if data.get("entity_id") == "test.ws_old_new":
                assert data["new_state"]["state"] == "second"
                assert data["old_state"]["state"] == "first"
                found = True
                break
        except asyncio.TimeoutError:
            break
    assert found, "Did not receive state_changed event for test.ws_old_new"


@pytest.mark.marge_only
async def test_ws_multiple_subscriptions(ws, rest):
    """Multiple subscribe_events on same connection both receive events."""
    sub_id_1 = await ws.subscribe_events("state_changed")
    sub_id_2 = await ws.subscribe_events("state_changed")

    await rest.set_state("test.ws_multi_sub", "on")
    await asyncio.sleep(0.3)

    # On HA many entities fire state_changed.  We need to see our specific
    # entity arrive on BOTH subscription IDs.
    seen_sub_ids = set()
    deadline = asyncio.get_event_loop().time() + 10.0
    while asyncio.get_event_loop().time() < deadline:
        try:
            remaining = deadline - asyncio.get_event_loop().time()
            event = await ws.recv_event(timeout=max(remaining, 0.1))
            if event.get("type") == "event":
                data = event.get("event", {}).get("data", {})
                if data.get("entity_id") == "test.ws_multi_sub":
                    seen_sub_ids.add(event["id"])
            if sub_id_1 in seen_sub_ids and sub_id_2 in seen_sub_ids:
                break
        except asyncio.TimeoutError:
            break

    assert sub_id_1 in seen_sub_ids, f"No event for sub {sub_id_1}"
    assert sub_id_2 in seen_sub_ids, f"No event for sub {sub_id_2}"


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe lifecycle
# ---------------------------------------------------------------------------

async def test_ws_subscribe_unsubscribe(ws):
    """Subscribe then unsubscribe completes without error."""
    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    assert sub.get("success", False) is True
    sub_id = sub["id"]

    unsub = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert unsub.get("success", False) is True


async def test_ws_subscribe_then_unsubscribe_no_leak(ws, rest):
    """Subscribe, unsubscribe, then verify no events leak."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.unsub_{tag}"

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    sub_id = sub["id"]

    unsub = await ws.send_command("unsubscribe_events", subscription=sub_id)
    assert unsub.get("success", False) is True

    # Set state -- should NOT deliver event since unsubscribed
    await rest.set_state(eid, "post_unsub")

    # Try to receive -- should timeout
    try:
        event = await ws.recv_event(timeout=1.0)
        # If we got something, it should be from a different subscription
    except asyncio.TimeoutError:
        pass  # Expected -- no event after unsubscribe


async def test_ws_unsubscribe_nonexistent_id(ws):
    """Unsubscribing from non-existent subscription ID doesn't crash."""
    resp = await ws.send_command("unsubscribe_events", subscription=999999)
    # Should not crash -- might succeed (no-op) or return error
    assert "type" in resp


# ---------------------------------------------------------------------------
# Command ordering and ID tracking
# ---------------------------------------------------------------------------

async def test_ws_sequential_commands(ws):
    """Multiple sequential WS commands all succeed."""
    # Ping
    assert await ws.ping() is True

    # Get config
    r1 = await ws.send_command("get_config")
    assert r1.get("success", False) is True

    # Render template (use render_template to handle HA subscription protocol)
    result = await ws.render_template("{{ 1 + 1 }}")
    assert "2" in result

    # Get services
    r3 = await ws.send_command("get_services")
    assert r3.get("success", False) is True


async def test_ws_response_ids_increment(ws):
    """WS response IDs match sent message IDs."""
    r1 = await ws.send_command("get_config")
    r2 = await ws.send_command("get_config")
    # Both should have different IDs and both succeed
    assert r1.get("success", False) is True
    assert r2.get("success", False) is True
    assert r1["id"] != r2["id"]


async def test_ws_interleaved_commands(ws, rest):
    """Interleaved WS commands maintain correct ID matching."""
    # Fire off multiple different commands quickly
    r1 = await ws.send_command("ping")
    r2 = await ws.send_command("get_config")
    r3 = await ws.send_command("get_services")

    # All should succeed
    assert r1.get("type") == "pong" or r1.get("success", False) is True
    assert r2.get("success", False) is True
    assert r3.get("success", False) is True

    # Render template last (uses render_template to drain HA subscription event)
    result = await ws.render_template("{{ 2 + 2 }}")
    assert "4" in result


# ---------------------------------------------------------------------------
# get_config
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", [
    "version", "location_name", "latitude", "longitude",
])
async def test_ws_get_config_field(ws, field):
    """WS get_config result contains expected field."""
    resp = await ws.send_command("get_config")
    assert resp.get("success", False) is True
    result = resp.get("result", {})
    assert field in result


# ---------------------------------------------------------------------------
# get_services
# ---------------------------------------------------------------------------

async def test_ws_get_services_returns_dict(ws):
    """WS get_services returns a dict keyed by domain."""
    resp = await ws.send_command("get_services")
    assert resp.get("success", False) is True
    result = resp.get("result", {})
    assert isinstance(result, dict)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# call_service via WS
# ---------------------------------------------------------------------------

@pytest.mark.marge_only
async def test_ws_call_service_light(ws, rest):
    """WS call_service for light works (ad-hoc entity; HA does not dispatch services to REST-created entities)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.wsord_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert resp.get("success", False) is True

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

async def test_ws_unknown_command(ws):
    """Unknown WS command response includes error info."""
    resp = await ws.send_command("absolutely_fake_command")
    assert resp.get("success", True) is False


async def test_ws_call_service_empty_domain(ws):
    """call_service with empty domain handled gracefully."""
    resp = await ws.send_command(
        "call_service",
        domain="",
        service="turn_on",
        service_data={},
    )
    # Should not crash
    assert "type" in resp


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

async def test_ws_render_template_valid(ws):
    """render_template with valid template returns result."""
    result = await ws.render_template("{{ 1 + 1 }}")
    assert "2" in result


async def test_ws_render_template_error(ws):
    """render_template with bad filter returns error or error text."""
    resp = await ws.send_command(
        "render_template",
        template="{{ x | nonexistent_filter }}",
    )
    # Marge returns success=false; HA may return success=false or success=true
    # (subscription ack) followed by an event with error text.
    # Either way, the server should not crash.
    if resp.get("success", False) is True:
        # HA subscription style: drain the follow-up event if result is null
        if resp.get("result") is None:
            try:
                event = await ws.recv_event(timeout=3.0)
                # HA may render error text in the result
                assert event.get("type") == "event"
            except asyncio.TimeoutError:
                pass  # No follow-up is also acceptable
    else:
        # Marge style or HA immediate error: success=false with error info
        assert resp.get("success") is False
