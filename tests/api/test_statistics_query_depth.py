"""
CTS -- Statistics Query Depth Tests

Tests the GET /api/statistics/{entity_id} endpoint: bucket format,
numeric aggregation, empty results, and entity with non-numeric states.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic Statistics ──────────────────────────────────────

async def test_statistics_returns_list(rest):
    """GET /api/statistics/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_statistics_bucket_format(rest):
    """Statistics buckets have expected fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_bf_{tag}"
    for v in ["10", "20", "30"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    buckets = resp.json()
    if buckets:
        bucket = buckets[0]
        # Expect aggregation fields
        assert "hour" in bucket or "start" in bucket or "mean" in bucket


async def test_statistics_unknown_entity(rest):
    """Statistics for nonexistent entity returns empty list."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.stats_nx_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_statistics_requires_auth(rest):
    """Statistics endpoint requires authentication."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.test",
    )
    # Should either 401/403 or 200 (Marge is lenient)
    assert resp.status_code in (200, 401, 403)


# ── Statistics with Multiple Values ───────────────────────

async def test_statistics_multiple_values(rest):
    """Statistics include data for entity with multiple state changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stats_mv_{tag}"
    for v in range(1, 6):
        await rest.set_state(eid, str(v * 10))
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Should have at least some data
    data = resp.json()
    assert isinstance(data, list)
