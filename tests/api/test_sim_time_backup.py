"""
CTS -- Sim-Time and Backup Tests

Tests simulation time management and backup/restore functionality.
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Sim-Time ─────────────────────────────────────────────

async def test_sim_time_set(rest):
    """POST /api/sim/time sets simulation time."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "14:30:00"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_sim_time_read_via_health(rest):
    """Sim-time appears in health endpoint."""
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "09:15:00"},
        headers=rest._headers(),
    )

    health = await rest.get_health()
    assert "sim_time" in health


async def test_sim_time_set_chapter(rest):
    """POST /api/sim/time with chapter sets chapter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "20:00:00", "chapter": "sunset"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_sim_time_set_speed(rest):
    """POST /api/sim/time with speed sets speed factor."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "12:00:00", "speed": 10},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_sim_time_partial_update(rest):
    """POST /api/sim/time with only chapter works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"chapter": "dawn"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Backup ───────────────────────────────────────────────

async def test_backup_returns_tarball(rest):
    """GET /api/backup returns tar.gz data."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # gzip magic bytes: 1f 8b
    assert resp.content[:2] == b'\x1f\x8b'


async def test_backup_has_content_type(rest):
    """Backup response has correct content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "gzip" in ct or "tar" in ct or "octet-stream" in ct


async def test_backup_not_empty(rest):
    """Backup data is non-trivial size."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert len(resp.content) > 100


# ── Prometheus Metrics ───────────────────────────────────

async def test_prometheus_metrics_endpoint(rest):
    """GET /metrics returns Prometheus text format."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "marge_entity_count" in text
    assert "marge_uptime_seconds" in text


async def test_prometheus_metrics_has_latency(rest):
    """Prometheus metrics include latency metric."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "marge_latency_avg_microseconds" in text


async def test_prometheus_metrics_content_type(rest):
    """Prometheus endpoint returns text content type."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    ct = resp.headers.get("content-type", "")
    assert "text" in ct
