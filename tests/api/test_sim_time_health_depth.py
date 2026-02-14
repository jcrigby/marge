"""
CTS -- Sim Time + Health Integration Depth Tests

Tests POST /api/sim/time endpoint for setting sim_time, sim_chapter,
sim_speed, and verifies these values appear in GET /api/health.
Also tests health endpoint invariants under various states.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _set_sim(rest, **kwargs):
    """Set sim values and return response."""
    body = {}
    if "time" in kwargs:
        body["time"] = kwargs["time"]
    if "chapter" in kwargs:
        body["chapter"] = kwargs["chapter"]
    if "speed" in kwargs:
        body["speed"] = kwargs["speed"]
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json=body,
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _get_health(rest):
    """Get health endpoint response."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    return resp.json()


# ── Set Sim Time ─────────────────────────────────────────

async def test_set_sim_time(rest):
    """POST /api/sim/time sets time and returns ok."""
    result = await _set_sim(rest, time="2026-02-14T10:00:00")
    assert result["status"] == "ok"


async def test_sim_time_in_health(rest):
    """Health endpoint reflects sim_time."""
    await _set_sim(rest, time="2026-02-14T14:30:00")
    health = await _get_health(rest)
    assert health["sim_time"] == "2026-02-14T14:30:00"


async def test_set_sim_chapter(rest):
    """POST /api/sim/time sets chapter."""
    await _set_sim(rest, chapter="morning")
    health = await _get_health(rest)
    assert health["sim_chapter"] == "morning"


async def test_set_sim_speed(rest):
    """POST /api/sim/time sets speed."""
    await _set_sim(rest, speed=10)
    health = await _get_health(rest)
    assert health["sim_speed"] == 10


async def test_set_all_sim_values(rest):
    """POST /api/sim/time sets time, chapter, and speed together."""
    await _set_sim(rest, time="2026-02-14T08:00:00", chapter="dawn", speed=5)
    health = await _get_health(rest)
    assert health["sim_time"] == "2026-02-14T08:00:00"
    assert health["sim_chapter"] == "dawn"
    assert health["sim_speed"] == 5


# ── Health Endpoint Fields ───────────────────────────────

async def test_health_has_status(rest):
    """Health response has status=ok."""
    health = await _get_health(rest)
    assert health["status"] == "ok"


async def test_health_has_uptime(rest):
    """Health response has uptime_seconds > 0."""
    health = await _get_health(rest)
    assert health["uptime_seconds"] > 0


async def test_health_has_entity_count(rest):
    """Health response has entity_count field."""
    health = await _get_health(rest)
    assert "entity_count" in health
    assert isinstance(health["entity_count"], int)


async def test_health_has_memory(rest):
    """Health response has memory_rss_kb > 0."""
    health = await _get_health(rest)
    assert health["memory_rss_kb"] > 0


async def test_health_has_latency(rest):
    """Health response has latency_avg_us field."""
    health = await _get_health(rest)
    assert "latency_avg_us" in health


async def test_health_has_state_changes(rest):
    """Health response has state_changes count."""
    health = await _get_health(rest)
    assert "state_changes" in health
    assert isinstance(health["state_changes"], int)


async def test_health_entity_count_after_create(rest):
    """Entity count in health increases after creating entities."""
    h1 = await _get_health(rest)
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.sim_health_{tag}", "1")
    h2 = await _get_health(rest)
    assert h2["entity_count"] >= h1["entity_count"] + 1


async def test_health_state_changes_after_set(rest):
    """State changes count in health increases after set_state."""
    h1 = await _get_health(rest)
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.sim_sc_{tag}", "1")
    h2 = await _get_health(rest)
    assert h2["state_changes"] >= h1["state_changes"] + 1
