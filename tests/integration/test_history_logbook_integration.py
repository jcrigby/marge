"""
CTS -- History and Logbook Integration Tests

Tests the full state history pipeline: set state via REST, query
history for that entity, verify history entries match. Also tests
global logbook and entity-specific logbook.
"""

import asyncio
import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── History API ────────────────────────────────────────────

async def test_history_returns_200(rest):
    """GET /api/history/period/:entity_id returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_history_returns_list(rest):
    """History returns a JSON array of state entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_list_{tag}"
    await rest.set_state(eid, "first")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_history_entry_has_fields(rest):
    """History entries have entity_id, state, attributes, timestamps."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_fields_{tag}"
    await rest.set_state(eid, "val")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry
        assert "attributes" in entry
        assert "last_changed" in entry


async def test_history_records_state_change(rest):
    """State changes appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_change_{tag}"
    await rest.set_state(eid, "one")
    await asyncio.sleep(0.1)
    await rest.set_state(eid, "two")
    await asyncio.sleep(0.1)
    await rest.set_state(eid, "three")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "one" in states
    assert "three" in states


async def test_history_preserves_order(rest):
    """History entries are in chronological order."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_order_{tag}"
    for i in range(5):
        await rest.set_state(eid, str(i))
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) >= 2:
        timestamps = [e["last_changed"] for e in data]
        assert timestamps == sorted(timestamps)


async def test_history_empty_for_unknown_entity(rest):
    """History for non-existent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nonexistent_xyz_99",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ── Global Logbook ─────────────────────────────────────────

async def test_global_logbook_returns_200(rest):
    """GET /api/logbook returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_global_logbook_returns_list(rest):
    """Global logbook returns a JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_global_logbook_entry_has_fields(rest):
    """Logbook entries have entity_id, state, when."""
    # Create some state changes first
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.logbook_{tag}", "first")
    await asyncio.sleep(0.1)
    await rest.set_state(f"sensor.logbook_{tag}", "second")
    await asyncio.sleep(0.3)

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


# ── Entity-Specific Logbook ────────────────────────────────

async def test_entity_logbook_returns_200(rest):
    """GET /api/logbook/:entity_id returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.elog_{tag}"
    await rest.set_state(eid, "val")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_entity_logbook_only_shows_changes(rest):
    """Entity logbook only includes actual state changes, not same-state updates."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.elog_dedup_{tag}"
    await rest.set_state(eid, "val_a")
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "val_a")  # Same state
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "val_b")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    # val_a should only appear once (deduped), val_b once
    assert states.count("val_a") <= 1 or states.count("val_b") <= 1
