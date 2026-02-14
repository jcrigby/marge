"""
CTS -- Prometheus Metrics Endpoint Depth Tests

Tests GET /metrics endpoint: response format, metric presence,
entity state metrics, and content-type.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Endpoint Basics ──────────────────────────────────────

async def test_metrics_returns_200(rest):
    """GET /metrics returns 200."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200


async def test_metrics_returns_text(rest):
    """GET /metrics returns text content."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    ct = resp.headers.get("content-type", "")
    assert "text" in ct


async def test_metrics_nonempty(rest):
    """GET /metrics returns non-empty content."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert len(resp.text.strip()) > 0


# ── Metric Content ───────────────────────────────────────

async def test_metrics_has_entity_count(rest):
    """Metrics include entity count metric."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "entity_count" in text or "entities" in text


async def test_metrics_has_state_changes(rest):
    """Metrics include state changes counter."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "state_change" in text


async def test_metrics_has_latency(rest):
    """Metrics include latency metric."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "latency" in text


# ── Entity State Metrics ────────────────────────────────

async def test_metrics_has_automation_triggers(rest):
    """Metrics include per-automation trigger counters."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    text = resp.text
    assert "automation_triggers_total" in text


async def test_metrics_no_auth_required(rest):
    """Metrics endpoint accessible without auth header."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
