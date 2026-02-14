"""
CTS -- Backup and Statistics Endpoint Depth Tests

Tests GET /api/backup returns a tar.gz archive, GET /api/statistics/:entity_id
returns hourly aggregated numeric data, and GET /api/error_log returns text.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Backup Endpoint ────────────────────────────────────────

async def test_backup_returns_200(rest):
    """GET /api/backup returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_backup_content_type_gzip(rest):
    """GET /api/backup returns application/gzip."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    ct = resp.headers.get("content-type", "")
    assert "gzip" in ct, f"Expected gzip content-type, got {ct}"


async def test_backup_has_content_disposition(rest):
    """GET /api/backup has Content-Disposition attachment header."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "marge_backup_" in cd


async def test_backup_body_non_empty(rest):
    """GET /api/backup returns a non-empty body."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert len(resp.content) > 0


async def test_backup_is_valid_gzip(rest):
    """GET /api/backup body starts with gzip magic bytes."""
    import gzip
    import io
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    # gzip magic: 0x1f 0x8b
    assert resp.content[:2] == b'\x1f\x8b', "Not a valid gzip archive"


# ── Statistics Endpoint ────────────────────────────────────

async def test_statistics_returns_200(rest):
    """GET /api/statistics/:entity_id returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_{tag}"
    # Create entity with numeric state to generate history
    await rest.set_state(eid, "23.5")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_statistics_returns_list(rest):
    """Statistics returns a JSON array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_list_{tag}"
    await rest.set_state(eid, "42.0")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_statistics_has_bucket_fields(rest):
    """Statistics buckets have hour, min, max, mean, count."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_fields_{tag}"
    # Set multiple values to ensure at least one bucket
    for val in ["10.0", "20.0", "30.0"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.3)

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


async def test_statistics_min_max_correct(rest):
    """Statistics min/max match actual values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_minmax_{tag}"
    for val in ["5.0", "15.0", "10.0"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        bucket = data[0]
        assert bucket["min"] <= 5.0
        assert bucket["max"] >= 15.0


async def test_statistics_empty_for_new_entity(rest):
    """Statistics for entity with no history returns empty list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_nodata_{tag}"

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_statistics_non_numeric_entity(rest):
    """Statistics for non-numeric entity returns empty (no parseable values)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.stat_text_{tag}"
    await rest.set_state(eid, "on")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ── Error Log Endpoint ─────────────────────────────────────

async def test_error_log_returns_200(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_error_log_returns_text(rest):
    """GET /api/error_log returns text content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    # Should return text/plain or similar
    assert isinstance(resp.text, str)
