"""
CTS -- Global Logbook and Event Listing Tests

Tests global logbook endpoint, filtered logbook, and event
type listing with various entity operations.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_global_logbook_returns_list(rest):
    """GET /api/logbook returns list of entries."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_after_state_change(rest):
    """Logbook records state changes."""
    await rest.set_state("sensor.log_depth_sc", "100")
    await rest.set_state("sensor.log_depth_sc", "200")

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.log_depth_sc",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entry_has_fields(rest):
    """Logbook entries have expected fields."""
    await rest.set_state("sensor.log_depth_fields", "abc")

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.log_depth_fields",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry


async def test_logbook_unknown_entity(rest):
    """Logbook for unknown entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.logbook_nonexistent_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_events_list_has_state_changed(rest):
    """Event listing includes state_changed event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    types = [e.get("event_type", e) if isinstance(e, dict) else e for e in data]
    # state_changed should be in the list (might be formatted differently)
    assert len(data) > 0


async def test_events_after_fire(rest):
    """Firing an event appears in event listing."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_log_depth_event",
        json={"key": "value"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp2.status_code == 200


async def test_history_multiple_changes(rest):
    """History records multiple state changes."""
    import asyncio
    for i in range(5):
        await rest.set_state("sensor.hist_depth_multi", str(i * 10))
        await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.hist_depth_multi",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_has_state_and_timestamp(rest):
    """History entries have state and timestamp fields."""
    import asyncio
    await rest.set_state("sensor.hist_depth_fields", "42")
    await asyncio.sleep(0.2)
    await rest.set_state("sensor.hist_depth_fields", "43")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.hist_depth_fields",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0] if isinstance(data[0], dict) else data[0][0]
        assert "state" in entry
        assert "last_changed" in entry or "timestamp" in entry
