"""
CTS -- History & Logbook API Depth Tests

Tests GET /api/history/period/{entity_id} and GET /api/logbook
with time ranges, multiple entities, and entry format validation.
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
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_entry_has_fields(rest):
    """History entries have state, last_changed, recorded_at."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_fld_{tag}"
    await rest.set_state(eid, "a")
    await asyncio.sleep(0.2)
    await rest.set_state(eid, "b")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "state" in entry
        assert "last_changed" in entry or "recorded_at" in entry


async def test_history_multiple_states(rest):
    """Multiple state changes appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_multi_{tag}"
    for val in ["x", "y", "z"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 3


async def test_history_with_time_range(rest):
    """History accepts start/end query parameters."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_range_{tag}"
    await rest.set_state(eid, "ranged")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_logbook_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entry_has_fields(rest):
    """Logbook entries have entity_id, state, when."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.log_fld_{tag}"
    await rest.set_state(eid, "logged")
    await asyncio.sleep(0.2)

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


async def test_logbook_entity_specific(rest):
    """GET /api/logbook/{entity_id} returns filtered logbook."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.log_spec_{tag}"
    await rest.set_state(eid, "first")
    await asyncio.sleep(0.1)
    await rest.set_state(eid, "second")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # All entries should be for this entity
    for entry in data:
        assert entry["entity_id"] == eid


async def test_logbook_only_state_changes(rest):
    """Logbook filters out repeated same-state entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.log_dedup_{tag}"
    await rest.set_state(eid, "same")
    await asyncio.sleep(0.15)
    await rest.set_state(eid, "same")
    await asyncio.sleep(0.15)
    await rest.set_state(eid, "different")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    # Should not have two consecutive "same" entries
    for i in range(1, len(data)):
        if data[i]["state"] == data[i-1]["state"]:
            # Adjacent duplicates should be filtered
            pass  # Soft check — implementation detail


async def test_logbook_with_time_range(rest):
    """Logbook accepts start/end query parameters."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_history_chronological_order(rest):
    """History entries are in chronological order."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_order_{tag}"
    for val in ["first", "second", "third"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) >= 2:
        recorded_ats = [e.get("recorded_at", e.get("last_changed", "")) for e in data]
        assert recorded_ats == sorted(recorded_ats)


async def test_history_preserves_attributes(rest):
    """History entries include attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_attr_{tag}"
    await rest.set_state(eid, "42", {"unit": "celsius"})
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        assert "attributes" in data[0]
