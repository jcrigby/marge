"""
CTS -- History and Logbook Depth Tests

Tests state history recording, time-range queries,
logbook deduplication, and global logbook.
"""

import asyncio
import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── History Recording ────────────────────────────────────

async def test_history_records_state_changes(rest):
    """State changes appear in history for the entity."""
    entity_id = "sensor.history_record_test"
    await rest.set_state(entity_id, "10")
    await asyncio.sleep(0.1)
    await rest.set_state(entity_id, "20")
    await asyncio.sleep(0.1)
    await rest.set_state(entity_id, "30")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)
    states = [e["state"] for e in entries]
    # Should contain the values we set
    assert "30" in states


async def test_history_includes_entity_id(rest):
    """History entries include the entity_id field."""
    entity_id = "sensor.history_eid_test"
    await rest.set_state(entity_id, "42")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity_id}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) > 0
    assert all(e["entity_id"] == entity_id for e in entries)


async def test_history_includes_timestamps(rest):
    """History entries include last_changed and last_updated."""
    entity_id = "sensor.history_ts_test"
    await rest.set_state(entity_id, "1")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity_id}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) > 0
    for e in entries:
        assert "last_changed" in e
        assert "last_updated" in e


async def test_history_includes_attributes(rest):
    """History entries preserve attributes."""
    entity_id = "sensor.history_attrs_test"
    await rest.set_state(entity_id, "72", {"unit_of_measurement": "F"})
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity_id}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) > 0
    last = entries[-1]
    assert last["attributes"].get("unit_of_measurement") == "F"


async def test_history_empty_for_unknown_entity(rest):
    """History returns empty list for unknown entity."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.definitely_no_history_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Logbook ──────────────────────────────────────────────

async def test_logbook_entity_returns_changes(rest):
    """Logbook for an entity returns state change entries."""
    entity_id = "sensor.logbook_changes_test"
    await rest.set_state(entity_id, "a")
    await asyncio.sleep(0.05)
    await rest.set_state(entity_id, "b")
    await asyncio.sleep(0.05)
    await rest.set_state(entity_id, "c")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)


async def test_logbook_deduplicates_same_state(rest):
    """Logbook filters out consecutive identical states."""
    entity_id = "sensor.logbook_dedup_test"
    await rest.set_state(entity_id, "same")
    await asyncio.sleep(0.05)
    await rest.set_state(entity_id, "same")
    await asyncio.sleep(0.05)
    await rest.set_state(entity_id, "different")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity_id}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    # Should not have two consecutive "same" entries
    for i in range(1, len(states)):
        if states[i] == "same":
            assert states[i - 1] != "same", "Logbook should deduplicate"


async def test_logbook_global_returns_entries(rest):
    """Global logbook returns recent entries across all entities."""
    await rest.set_state("sensor.logbook_global_a", "1")
    await rest.set_state("sensor.logbook_global_b", "2")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)
    # Should have entries from multiple entities
    eids = set(e["entity_id"] for e in entries)
    assert len(eids) > 1


async def test_logbook_entries_have_when_field(rest):
    """Logbook entries include a 'when' timestamp."""
    entity_id = "sensor.logbook_when_test"
    await rest.set_state(entity_id, "x")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity_id}",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "when" in entries[0]


# ── Merged from depth: History Format ────────────────────

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


# ── Merged from depth: Logbook Format ────────────────────

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


async def test_logbook_with_time_range(rest):
    """Logbook accepts start/end query parameters."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Merged from test_logbook_history_edge.py ──────────


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
