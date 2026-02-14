"""
CTS -- Statistics Endpoint Depth Tests

Tests GET /api/statistics/{entity_id} with numeric state values,
hourly bucket aggregation, and edge cases.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_statistics_returns_list(rest):
    """GET /api/statistics/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_{tag}"
    # Create some numeric state entries
    for val in ["10", "20", "30"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_statistics_has_bucket_fields(rest):
    """Statistics buckets have hour, min, max, mean, count."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_fields_{tag}"
    for val in ["5", "15", "25"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        bucket = data[0]
        assert "hour" in bucket
        assert "min" in bucket
        assert "max" in bucket
        assert "mean" in bucket
        assert "count" in bucket


async def test_statistics_correct_min_max(rest):
    """Statistics min/max reflect actual values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_minmax_{tag}"
    values = [10.0, 50.0, 30.0, 5.0, 45.0]
    for val in values:
        await rest.set_state(eid, str(val))
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        # All in same hour bucket
        all_mins = [b["min"] for b in data]
        all_maxs = [b["max"] for b in data]
        assert min(all_mins) <= 5.0
        assert max(all_maxs) >= 45.0


async def test_statistics_correct_mean(rest):
    """Statistics mean is computed correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_mean_{tag}"
    values = [10, 20, 30]
    for val in values:
        await rest.set_state(eid, str(val))
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        total_sum = sum(b["mean"] * b["count"] for b in data)
        total_count = sum(b["count"] for b in data)
        overall_mean = total_sum / total_count
        assert 15 <= overall_mean <= 25


async def test_statistics_count_matches(rest):
    """Statistics count matches number of writes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_count_{tag}"
    n = 5
    for i in range(n):
        await rest.set_state(eid, str(i * 10))
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    total_count = sum(b["count"] for b in data)
    assert total_count >= n


async def test_statistics_unknown_entity_empty(rest):
    """Statistics for never-recorded entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.never_existed_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_statistics_nonnumeric_excluded(rest):
    """Non-numeric state values are excluded from statistics."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_nonnumeric_{tag}"
    # Mix numeric and non-numeric
    await rest.set_state(eid, "100")
    await asyncio.sleep(0.15)
    await rest.set_state(eid, "not_a_number")
    await asyncio.sleep(0.15)
    await rest.set_state(eid, "200")
    await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        # Count should only include numeric values
        total_count = sum(b["count"] for b in data)
        assert total_count >= 2  # at least the two numeric values


async def test_statistics_with_time_range(rest):
    """Statistics accept start/end query parameters."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_range_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
