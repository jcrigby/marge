"""
CTS -- Sim-Time Endpoint Depth Tests

Tests the POST /api/sim/time endpoint for setting simulation time,
chapter, and speed. Verifies health endpoint reflects these values.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Set Sim Time ──────────────────────────────────────────

async def test_set_sim_time(rest):
    """POST /api/sim/time sets sim time."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "12:00:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_sim_time_reflected_in_health(rest):
    """Set sim time appears in health endpoint."""
    tag = uuid.uuid4().hex[:8]
    time_val = f"14:{tag[:2]}:00"
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": time_val},
    )
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    health = resp.json()
    assert health.get("sim_time") == time_val


# ── Set Chapter ───────────────────────────────────────────

async def test_set_sim_chapter(rest):
    """POST /api/sim/time with chapter sets chapter."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"chapter": f"test_{tag}"},
    )
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    health = resp.json()
    assert health.get("sim_chapter") == f"test_{tag}"


# ── Set Speed ─────────────────────────────────────────────

async def test_set_sim_speed(rest):
    """POST /api/sim/time with speed sets sim speed."""
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"speed": 10},
    )
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    health = resp.json()
    assert health.get("sim_speed") == 10
    # Reset to 1
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"speed": 1},
    )


# ── Combined ──────────────────────────────────────────────

async def test_set_all_sim_fields(rest):
    """Setting time, chapter, and speed together works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "08:30:00", "chapter": "morning", "speed": 5},
    )
    assert resp.status_code == 200
    health = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    assert health.get("sim_time") == "08:30:00"
    assert health.get("sim_chapter") == "morning"
    assert health.get("sim_speed") == 5
    # Reset
    await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"speed": 1, "chapter": "", "time": ""},
    )


# ── Health Fields ─────────────────────────────────────────

async def test_health_has_sim_fields(rest):
    """Health endpoint includes sim_time and sim_chapter."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    health = resp.json()
    assert "sim_time" in health
    assert "sim_chapter" in health


async def test_health_has_ws_connections(rest):
    """Health endpoint includes ws_connections."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    health = resp.json()
    assert "ws_connections" in health
    assert isinstance(health["ws_connections"], int)
