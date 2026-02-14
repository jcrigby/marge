"""
CTS -- Logbook & History Edge Case Tests

Tests history and logbook endpoints with time ranges, empty results,
multiple state changes, and global logbook behavior.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_history_returns_list(rest):
    """GET /api/history/period/{eid} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_{tag}"
    await rest.set_state(eid, "val1")

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_records_state_changes(rest):
    """Multiple state changes appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.histmulti_{tag}"

    for val in ["a", "b", "c", "d"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.05)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    # Should have multiple entries
    assert len(data) >= 2


async def test_history_entry_has_expected_fields(rest):
    """History entries have entity_id, state, last_changed, last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.histfield_{tag}"
    await rest.set_state(eid, "val")

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry
        assert "last_changed" in entry
        assert "last_updated" in entry
        assert entry["entity_id"] == eid


async def test_history_nonexistent_entity_empty(rest):
    """History for nonexistent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.definitely_nonexistent_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


async def test_history_with_time_range(rest):
    """History with start/end query params works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.histtime_{tag}"
    await rest.set_state(eid, "v")

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2099-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_history_future_range_empty(rest):
    """History with future time range returns empty."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.histfuture_{tag}"
    await rest.set_state(eid, "v")

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2099-01-01T00:00:00Z", "end": "2099-12-31T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


async def test_logbook_global_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_global_entry_format(rest):
    """Logbook entries have entity_id, state, when."""
    # Trigger a state change so there's something in the logbook
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbentry_{tag}"
    await rest.set_state(eid, "v1")
    await asyncio.sleep(0.1)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry
        assert "when" in entry


async def test_logbook_entity_returns_list(rest):
    """GET /api/logbook/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbeid_{tag}"
    await rest.set_state(eid, "x")

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entity_records_changes(rest):
    """Entity logbook records state transitions."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbchanges_{tag}"

    for val in ["a", "b", "c"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.05)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    # Should capture transitions
    assert len(data) >= 1


async def test_logbook_with_time_range(rest):
    """Logbook with start/end query params works."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        params={"start": "2020-01-01T00:00:00Z", "end": "2099-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
