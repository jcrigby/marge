"""
CTS -- Health Endpoint Depth Tests

Tests GET /api/health response format, metric fields, and
Prometheus /metrics endpoint format.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── GET /api/health ─────────────────────────────────────────

async def test_health_returns_200(rest):
    """GET /api/health returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_health_has_uptime(rest):
    """Health response includes uptime field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "uptime_seconds" in data or "uptime" in data


async def test_health_has_rss(rest):
    """Health response includes memory RSS field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "rss_kb" in data or "rss_mb" in data or "memory" in str(data).lower()


async def test_health_has_state_changes(rest):
    """Health response includes state_changes metric."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "state_changes" in data


async def test_health_has_entity_count(rest):
    """Health response includes entity count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "entity_count" in data or "entities" in data


async def test_health_state_changes_nonnegative(rest):
    """state_changes is a non-negative integer."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["state_changes"] >= 0


# ── GET /metrics ────────────────────────────────────────────

async def test_metrics_returns_200(rest):
    """GET /metrics returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_metrics_is_text(rest):
    """GET /metrics returns text/plain content."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert "text" in resp.headers.get("content-type", "")


async def test_metrics_has_state_changes(rest):
    """Prometheus metrics include marge_state_changes."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert "marge_state_changes" in resp.text or "state_changes" in resp.text


async def test_metrics_has_uptime(rest):
    """Prometheus metrics include uptime metric."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert "uptime" in resp.text


async def test_metrics_has_rss(rest):
    """Prometheus metrics include memory RSS metric."""
    resp = await rest.client.get(
        f"{rest.base_url}/metrics",
        headers=rest._headers(),
    )
    assert "rss" in resp.text.lower()
