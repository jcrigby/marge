"""
CTS -- History Time Window Depth Tests

Tests history and logbook with combined start+end parameters,
narrow time windows, chronological ordering, and boundary
conditions for time-filtered queries.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest

pytestmark = pytest.mark.asyncio


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _iso_past(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _iso_future(minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


# ── History with Start + End ───────────────────────────────

async def test_history_start_and_end_both(rest):
    """History with both start and end returns entries in that window."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_se_{tag}"
    await rest.set_state(eid, "100")
    await asyncio.sleep(0.3)

    start = _iso_past(5)
    end = _iso_future(5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
    assert entries[0]["state"] == "100"


async def test_history_narrow_window_captures(rest):
    """History with narrow window around now captures recent state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_narrow_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)

    start = _iso_past(1)
    end = _iso_future(1)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start={start}&end={end}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1


async def test_history_past_window_empty(rest):
    """History with past-only window returns empty for recent entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_past_{tag}"
    await rest.set_state(eid, "X")
    await asyncio.sleep(0.3)

    start = "2020-01-01T00:00:00Z"
    end = "2020-01-02T00:00:00Z"
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_history_future_window_empty(rest):
    """History with future window returns empty."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_future_{tag}"
    await rest.set_state(eid, "Y")
    await asyncio.sleep(0.3)

    start = "2099-01-01T00:00:00Z"
    end = "2099-12-31T00:00:00Z"
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── History Ordering ───────────────────────────────────────

async def test_history_entries_chronological(rest):
    """History entries are in chronological order (oldest first)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_order_{tag}"
    for i in range(5):
        await rest.set_state(eid, str(i * 10))
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    timestamps = [e["last_changed"] for e in entries]
    assert timestamps == sorted(timestamps)


async def test_history_multiple_states_all_recorded(rest):
    """Multiple state changes all appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_multi_{tag}"
    values = ["alpha", "beta", "gamma", "delta"]
    for v in values:
        await rest.set_state(eid, v)
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    recorded_states = [e["state"] for e in entries]
    for v in values:
        assert v in recorded_states


# ── Logbook with Start + End ──────────────────────────────

async def test_logbook_global_start_and_end(rest):
    """Global logbook with start+end returns entries in window."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_lb_se_{tag}"
    await rest.set_state(eid, "logged")
    await asyncio.sleep(0.3)

    start = _iso_past(5)
    end = _iso_future(5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert isinstance(entries, list)
    eids = {e["entity_id"] for e in entries}
    assert eid in eids


async def test_logbook_entity_start_and_end(rest):
    """Entity logbook with start+end returns filtered entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_lb_eid_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    await asyncio.sleep(0.3)

    start = _iso_past(5)
    end = _iso_future(5)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}?start={start}&end={end}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 2
    states = [e["state"] for e in entries]
    assert "A" in states
    assert "B" in states


async def test_logbook_global_past_window(rest):
    """Global logbook with past window returns no recent entries."""
    start = "2020-01-01T00:00:00Z"
    end = "2020-01-02T00:00:00Z"
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── History Entry Fields ────────────────────────────────────

async def test_history_entry_has_entity_id(rest):
    """All history entries have the queried entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_eid_{tag}"
    await rest.set_state(eid, "1")
    await rest.set_state(eid, "2")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    for e in entries:
        assert e["entity_id"] == eid


async def test_history_entry_has_last_updated(rest):
    """History entries have last_updated field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htw_lu_{tag}"
    await rest.set_state(eid, "val")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "last_updated" in entries[0]
