"""
CTS -- Config Check, Error Log, Backup, and Prometheus Depth Tests

Tests POST /api/config/core/check_config, GET /api/error_log,
GET /api/backup (backup archive), and GET /metrics (Prometheus format)
for detailed field verification.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── check_config ────────────────────────────────────────

async def test_check_config_returns_valid(rest):
    """POST /api/config/core/check_config returns result=valid."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "valid"


async def test_check_config_has_errors_field(rest):
    """check_config response has errors field (null when valid)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "errors" in data


# ── error_log ───────────────────────────────────────────

async def test_error_log_returns_200(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_error_log_returns_string(rest):
    """GET /api/error_log returns a string (may be empty)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert isinstance(resp.text, str)


# ── Prometheus Metrics ──────────────────────────────────

async def test_prometheus_returns_text(rest):
    """GET /metrics returns text/plain."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")


async def test_prometheus_has_marge_info(rest):
    """Prometheus metrics include marge_info."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "marge_info" in text


async def test_prometheus_has_uptime(rest):
    """Prometheus metrics include marge_uptime_seconds."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_uptime_seconds" in resp.text


async def test_prometheus_has_entity_count(rest):
    """Prometheus metrics include marge_entity_count."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_entity_count" in resp.text


async def test_prometheus_has_state_changes(rest):
    """Prometheus metrics include marge_state_changes_total."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_state_changes_total" in resp.text


async def test_prometheus_has_latency(rest):
    """Prometheus metrics include latency gauges."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_latency_avg_microseconds" in resp.text
    assert "marge_latency_max_microseconds" in resp.text


async def test_prometheus_has_memory(rest):
    """Prometheus metrics include marge_memory_rss_bytes."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_memory_rss_bytes" in resp.text


async def test_prometheus_has_ws_connections(rest):
    """Prometheus metrics include marge_ws_connections."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_ws_connections" in resp.text


async def test_prometheus_has_automation_triggers(rest):
    """Prometheus metrics include marge_automation_triggers_total."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_automation_triggers_total" in resp.text


async def test_prometheus_has_startup(rest):
    """Prometheus metrics include marge_startup_seconds."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert "marge_startup_seconds" in resp.text


# ── Backup ──────────────────────────────────────────────

async def test_backup_returns_gzip(rest):
    """GET /api/backup returns a gzip file."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "gzip" in resp.headers.get("content-type", "")


async def test_backup_has_disposition(rest):
    """GET /api/backup has Content-Disposition with filename."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert "content-disposition" in resp.headers
    assert "marge_backup_" in resp.headers["content-disposition"]


async def test_backup_has_content(rest):
    """GET /api/backup returns non-empty body."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert len(resp.content) > 0
