"""
CTS -- History and Logbook Depth Tests

Tests state history recording, time-range queries,
logbook deduplication, and global logbook.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


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
