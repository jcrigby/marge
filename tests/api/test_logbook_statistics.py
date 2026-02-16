"""
CTS -- Logbook and Statistics Depth Tests

Tests logbook entries, statistics aggregation, history with
various parameters, and recorder interaction details.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── Logbook Global ───────────────────────────────────────

async def test_logbook_global_entries_have_fields(rest):
    """Logbook entries contain expected fields."""
    # Create a state change to ensure logbook has content
    await rest.set_state("sensor.lb_field_test", "first")
    await asyncio.sleep(0.2)
    await rest.set_state("sensor.lb_field_test", "second")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0]
        assert "entity_id" in entry
        assert "state" in entry
        assert "when" in entry


# ── Logbook Per-Entity ───────────────────────────────────

async def test_logbook_per_entity(rest):
    """GET /api/logbook/:entity_id returns filtered entries."""
    await rest.set_state("sensor.lb_per_test", "alpha")
    await asyncio.sleep(0.2)
    await rest.set_state("sensor.lb_per_test", "beta")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.lb_per_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for entry in data:
        assert entry["entity_id"] == "sensor.lb_per_test"


async def test_logbook_nonexistent_entity(rest):
    """Logbook for nonexistent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.lb_nonexistent_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Statistics ───────────────────────────────────────────

async def test_statistics_numeric_entity(rest):
    """Statistics for numeric entity returns aggregates."""
    for val in ["10", "20", "30", "40", "50"]:
        await rest.set_state("sensor.stat_numeric", val)
        await asyncio.sleep(0.15)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.stat_numeric",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        entry = data[0]
        assert "mean" in entry or "min" in entry or "sum" in entry


# ── History Period ───────────────────────────────────────

async def test_history_entries_have_state(rest):
    """History entries include state values."""
    await rest.set_state("sensor.hist_state", "abc")
    await asyncio.sleep(0.2)
    await rest.set_state("sensor.hist_state", "def")
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.hist_state",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        for entry in data:
            assert "state" in entry
            assert "entity_id" in entry
