"""
CTS -- Health and Metrics Endpoint Detail Depth Tests

Tests GET /api/health response fields (status, version, entity_count,
memory, uptime, latency, sim_time, ws_connections), and verifies
metrics change after state operations.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Health Endpoint Fields ──────────────────────────────

async def test_health_returns_ok(rest):
    """GET /api/health returns status ok."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_has_version(rest):
    """Health response has version string."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "version" in data
    assert isinstance(data["version"], str)


async def test_health_has_entity_count(rest):
    """Health response has entity_count."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "entity_count" in data
    assert isinstance(data["entity_count"], int)


async def test_health_has_memory(rest):
    """Health response has memory fields."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "memory_rss_kb" in data
    assert "memory_rss_mb" in data
    assert data["memory_rss_kb"] > 0


async def test_health_has_uptime(rest):
    """Health response has uptime_seconds."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


async def test_health_has_startup(rest):
    """Health response has startup_us and startup_ms."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "startup_us" in data
    assert "startup_ms" in data


async def test_health_has_latency(rest):
    """Health response has latency_avg_us and latency_max_us."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "latency_avg_us" in data
    assert "latency_max_us" in data


async def test_health_has_state_changes(rest):
    """Health response has state_changes and events_fired."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "state_changes" in data
    assert "events_fired" in data


async def test_health_has_sim_fields(rest):
    """Health response has sim_time, sim_chapter, sim_speed."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "sim_time" in data
    assert "sim_chapter" in data
    assert "sim_speed" in data


async def test_health_has_ws_connections(rest):
    """Health response has ws_connections."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    data = resp.json()
    assert "ws_connections" in data


# ── Metrics Change After Operations ─────────────────────

async def test_state_changes_increase(rest):
    """state_changes metric increases after state operations."""
    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.hm_{tag}", "1")
    h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    assert h2["state_changes"] > h1["state_changes"]


async def test_entity_count_reflects_creation(rest):
    """entity_count increases after creating new entities."""
    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.hmc_{tag}", "1")
    h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    assert h2["entity_count"] >= h1["entity_count"] + 1


# ── No Auth Required ────────────────────────────────────

async def test_health_no_auth_required(rest):
    """Health endpoint accessible without auth header."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
