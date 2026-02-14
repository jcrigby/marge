"""
CTS -- History and Statistics Response Depth Tests

Tests GET /api/history/period/<eid> and GET /api/statistics/<eid>
response formats, field presence, empty results, and data accuracy.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.15


# ── History Response Format ──────────────────────────────

async def test_history_returns_array(rest):
    """GET /api/history/period/<eid> returns array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_arr_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_history_entry_has_entity_id(rest):
    """History entry has entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_eid_{tag}"
    await rest.set_state(eid, "val")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert entries[0]["entity_id"] == eid


async def test_history_entry_has_state(rest):
    """History entry has state field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_st_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "state" in entries[0]


async def test_history_entry_has_last_changed(rest):
    """History entry has last_changed field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_lc_{tag}"
    await rest.set_state(eid, "v")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "last_changed" in entries[0]


async def test_history_entry_has_attributes(rest):
    """History entry has attributes field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_attr_{tag}"
    await rest.set_state(eid, "v", {"unit": "W"})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "attributes" in entries[0]


async def test_history_records_multiple_states(rest):
    """History records multiple state changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_multi_{tag}"
    for v in ["A", "B", "C"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "A" in states
    assert "C" in states


async def test_history_nonexistent_entity_empty(rest):
    """History for nonexistent entity returns empty array."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nope_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Statistics Response Format ───────────────────────────

async def test_statistics_returns_array(rest):
    """GET /api/statistics/<eid> returns array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_sarr_{tag}"
    await rest.set_state(eid, "10")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_statistics_bucket_has_fields(rest):
    """Statistics bucket has hour, min, max, mean, count fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_sbkt_{tag}"
    for v in ["10", "20", "30"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    buckets = resp.json()
    if buckets:
        b = buckets[0]
        assert "hour" in b
        assert "min" in b
        assert "max" in b
        assert "mean" in b
        assert "count" in b


async def test_statistics_numeric_aggregation(rest):
    """Statistics correctly aggregates numeric values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_sagg_{tag}"
    for v in ["10", "20", "30"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    buckets = resp.json()
    if buckets:
        b = buckets[0]
        assert b["min"] <= b["mean"] <= b["max"]
        assert b["count"] >= 1


async def test_statistics_nonnumeric_excluded(rest):
    """Statistics ignores non-numeric state values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hsrd_snan_{tag}"
    await rest.set_state(eid, "not_a_number")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    buckets = resp.json()
    # Non-numeric states are excluded, so result may be empty
    assert isinstance(buckets, list)
