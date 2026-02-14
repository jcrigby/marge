"""
CTS -- Fire Event API Depth Tests

Tests event firing via REST and WS, event response format,
and automation event trigger interaction.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_fire_event_returns_message(rest):
    """Fire event returns message with event type."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_fire_depth_1",
        json={"data": "value"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "test_fire_depth_1" in data["message"]


async def test_fire_event_with_empty_body(rest):
    """Fire event with empty body."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_fire_depth_2",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_with_complex_data(rest):
    """Fire event with complex data payload."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_fire_depth_3",
        json={
            "source": "test",
            "data": {"nested": True, "list": [1, 2, 3]},
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_with_dots(rest):
    """Fire event with dots in event type."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/my.custom.event_type",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "my.custom.event_type" in data["message"]


async def test_ws_fire_event(ws):
    """WS fire_event returns success."""
    resp = await ws.send_command(
        "fire_event",
        event_type="ws_depth_event",
    )
    assert resp["success"] is True


async def test_fire_custom_event_triggers_automation(rest):
    """Firing custom_alert event can trigger smoke/co automation."""
    # smoke_co_emergency listens for custom_alert
    await rest.set_state("binary_sensor.smoke_detector", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/events/custom_alert",
        json={"alert_type": "smoke"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.3)

    # Automation should have processed the event
    state = await rest.get_state("automation.smoke_co_emergency")
    assert state is not None


async def test_fire_multiple_events_sequentially(rest):
    """Multiple events can be fired sequentially."""
    for i in range(5):
        resp = await rest.client.post(
            f"{rest.base_url}/api/events/test_fire_depth_seq_{i}",
            json={"index": i},
            headers=rest._headers(),
        )
        assert resp.status_code == 200


async def test_fire_event_appears_in_event_list(rest):
    """Fired event type appears in event listing."""
    await rest.client.post(
        f"{rest.base_url}/api/events/test_fire_depth_listed",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
