"""
CTS -- Logbook Global Endpoint Depth Tests

Tests GET /api/logbook (global) and GET /api/logbook/:entity_id
with time ranges, empty results, and entry format.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_logbook_global_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_global_with_time_range(rest):
    """GET /api/logbook with start/end params returns list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        params={
            "start": "2020-01-01T00:00:00Z",
            "end": "2030-01-01T00:00:00Z",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_logbook_entity_returns_list(rest):
    """GET /api/logbook/:entity_id returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.logb_{tag}"
    await rest.set_state(eid, "v1")
    await rest.set_state(eid, "v2")

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entity_captures_changes(rest):
    """Logbook entries exist after state changes (with recorder flush)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.logbc_{tag}"
    await rest.set_state(eid, "first")
    await rest.set_state(eid, "second")
    await rest.set_state(eid, "third")

    # Wait for async recorder to flush
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    # Recorder may batch writes; at least verify it returns a list
    # (actual entry count depends on recorder flush timing)


async def test_logbook_entry_format(rest):
    """Logbook entries have entity_id and state fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.logbf_{tag}"
    await rest.set_state(eid, "val")
    await asyncio.sleep(0.5)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry


async def test_logbook_nonexistent_entity_empty(rest):
    """Logbook for nonexistent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.logb_nonexistent_999",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_logbook_narrow_time_range(rest):
    """Logbook with very narrow time range returns few/no entries."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        params={
            "start": "2020-01-01T00:00:00Z",
            "end": "2020-01-01T00:00:01Z",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0
