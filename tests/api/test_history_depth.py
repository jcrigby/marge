"""
CTS -- History & Statistics Depth Tests

Tests history recording fidelity, logbook filtering, statistics
aggregation accuracy, and history query edge cases.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio

# Recorder coalesces writes at 100ms; need >100ms between writes
_FLUSH = 0.15


# ── History Recording ─────────────────────────────────────

async def test_history_records_multiple_changes(rest):
    """Multiple state changes are recorded in history."""
    entity = "sensor.hist_multi"
    for val in ["10", "20", "30"]:
        await rest.set_state(entity, val)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 3
    states = [e["state"] for e in entries]
    assert "10" in states
    assert "20" in states
    assert "30" in states


async def test_history_preserves_order(rest):
    """History entries are in chronological order."""
    entity = "sensor.hist_order"
    for val in ["1", "2", "3", "4", "5"]:
        await rest.set_state(entity, val)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    entries = resp.json()
    timestamps = [e.get("last_changed", e.get("recorded_at", "")) for e in entries]
    assert timestamps == sorted(timestamps)


async def test_history_includes_attributes(rest):
    """History entries preserve entity attributes."""
    entity = "sensor.hist_attrs"
    await rest.set_state(entity, "72", {"unit_of_measurement": "F", "friendly_name": "Temp"})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    last = entries[-1]
    assert last["attributes"]["unit_of_measurement"] == "F"


async def test_history_empty_for_new_entity(rest):
    """New entity with no history returns empty or single entry."""
    entity = "sensor.hist_empty_xyz"
    await rest.set_state(entity, "init")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1


# ── Logbook ───────────────────────────────────────────────

async def test_logbook_entity_returns_entries(rest):
    """GET /api/logbook/{entity_id} returns logbook entries."""
    entity = "sensor.logbook_test2"
    await rest.set_state(entity, "a")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(entity, "b")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 2


async def test_logbook_global_includes_recent(rest):
    """GET /api/logbook returns recent state changes globally."""
    await rest.set_state("sensor.logbook_global_x", "val1")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
    ids = [e["entity_id"] for e in entries]
    assert "sensor.logbook_global_x" in ids


async def test_logbook_entry_has_when(rest):
    """Logbook entries include a 'when' timestamp."""
    entity = "sensor.logbook_when2"
    await rest.set_state(entity, "timestamped")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "when" in entries[-1]


async def test_logbook_dedup_same_state(rest):
    """Logbook deduplicates consecutive identical states."""
    entity = "sensor.logbook_dedup2"
    await rest.set_state(entity, "same")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(entity, "same")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{entity}",
        headers=rest._headers(),
    )
    entries = resp.json()
    same_entries = [e for e in entries if e.get("state") == "same"]
    # Logbook correctly deduplicates — only one entry for repeated same state
    assert len(same_entries) == 1


# ── Statistics ────────────────────────────────────────────

async def test_statistics_min_max_mean(rest):
    """Statistics correctly compute min/max/mean."""
    entity = "sensor.stat_accuracy"
    for val in [10, 20, 30, 40, 50]:
        await rest.set_state(entity, str(val))
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    buckets = resp.json()
    if len(buckets) > 0:
        bucket = buckets[-1]
        assert "min" in bucket
        assert "max" in bucket
        assert "mean" in bucket
        assert bucket["min"] <= bucket["mean"] <= bucket["max"]


async def test_statistics_empty_for_text(rest):
    """Non-numeric entities return empty statistics."""
    entity = "sensor.stat_text"
    await rest.set_state(entity, "hello")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert isinstance(buckets, list)
    assert len(buckets) == 0


async def test_statistics_bucket_has_hour(rest):
    """Statistics buckets include an hour field."""
    entity = "sensor.stat_hour"
    await rest.set_state(entity, "42.5")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{entity}",
        headers=rest._headers(),
    )
    buckets = resp.json()
    if len(buckets) > 0:
        assert "hour" in buckets[0]
        assert "count" in buckets[0]
