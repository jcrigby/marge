"""
CTS -- API Latency Depth Tests

Tests that API endpoints respond within reasonable latency bounds.
Measures response times for common operations: state read/write,
service calls, template renders, and health checks.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Health Check Latency ──────────────────────────────────

async def test_health_latency(rest):
    """Health endpoint responds in < 100ms."""
    t0 = time.monotonic()
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.1


async def test_api_status_latency(rest):
    """API status responds in < 50ms."""
    t0 = time.monotonic()
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.05


# ── State Read/Write Latency ─────────────────────────────

async def test_state_write_latency(rest):
    """State write responds in < 50ms."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lat_w_{tag}"
    t0 = time.monotonic()
    await rest.set_state(eid, "42")
    elapsed = time.monotonic() - t0
    assert elapsed < 0.05


async def test_state_read_latency(rest):
    """State read responds in < 50ms."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lat_r_{tag}"
    await rest.set_state(eid, "42")
    t0 = time.monotonic()
    state = await rest.get_state(eid)
    elapsed = time.monotonic() - t0
    assert state is not None
    assert elapsed < 0.05


# ── Service Call Latency ──────────────────────────────────

async def test_service_call_latency(rest):
    """Service call responds in < 100ms."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lat_svc_{tag}"
    await rest.set_state(eid, "off")
    t0 = time.monotonic()
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    elapsed = time.monotonic() - t0
    assert elapsed < 0.1


# ── Template Render Latency ───────────────────────────────

async def test_template_latency(rest):
    """Template render responds in < 100ms."""
    t0 = time.monotonic()
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ 2 + 2 }}"},
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.1


async def test_template_state_query_latency(rest):
    """Template with state query responds in < 100ms."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lat_tpl_{tag}"
    await rest.set_state(eid, "42")
    t0 = time.monotonic()
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": f"{{{{ states('{eid}') }}}}"},
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.1


# ── Search Latency ────────────────────────────────────────

async def test_search_latency(rest):
    """Search with domain filter responds in < 200ms."""
    t0 = time.monotonic()
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor",
        headers=rest._headers(),
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.2


# ── Config Endpoint Latency ───────────────────────────────

async def test_config_latency(rest):
    """Config endpoint responds in < 50ms."""
    t0 = time.monotonic()
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    elapsed = time.monotonic() - t0
    assert resp.status_code == 200
    assert elapsed < 0.05
