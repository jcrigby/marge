"""
CTS -- Events Listing & Fire Event Depth Tests

Tests GET /api/events listing, POST /api/events/{type} firing,
event types, and event data payload handling.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_events_listing_returns_list(rest):
    """GET /api/events returns list of event types."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_events_listing_has_standard_types(rest):
    """Events listing includes standard HA event types."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    event_names = [e["event"] for e in data]
    assert "state_changed" in event_names
    assert "call_service" in event_names


async def test_events_listing_has_automation_event(rest):
    """Events listing includes automation_triggered."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    event_names = [e["event"] for e in data]
    assert "automation_triggered" in event_names


async def test_events_listing_entry_format(rest):
    """Event listing entries have event and listener_count fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "event" in entry
        assert "listener_count" in entry


async def test_fire_event_returns_message(rest):
    """POST /api/events/{type} returns message."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/custom_event_{tag}",
        json={"data": {"key": "value"}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


async def test_fire_event_with_empty_data(rest):
    """Fire event with empty data object."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/empty_event_{tag}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_with_complex_data(rest):
    """Fire event with nested data structure."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/complex_event_{tag}",
        json={
            "nested": {"deep": {"key": "value"}},
            "array": [1, 2, 3],
            "number": 42.5,
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_ws(ws):
    """WS fire_event fires an event."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "fire_event",
        event_type=f"ws_fire_{tag}",
        event_data={"source": "ws_test"},
    )
    assert resp.get("success", False) is True


async def test_fire_event_message_contains_type(rest):
    """Fire event response message references the event type."""
    tag = uuid.uuid4().hex[:8]
    event_type = f"msg_check_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/{event_type}",
        json={},
        headers=rest._headers(),
    )
    data = resp.json()
    assert event_type in data["message"]


async def test_fire_event_with_dots_in_type(rest):
    """Event type with dots works correctly."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/custom.dotted.event",
        json={"key": "val"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
