"""
CTS -- History API Parameter Tests

Tests history endpoint with various time range parameters,
default behavior, and edge cases.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.15


async def test_history_default_range(rest):
    """GET /api/history/period/:id without params returns recent data."""
    entity = "sensor.hist_param_default"
    await rest.set_state(entity, "baseline")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(entity, "recent")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_history_with_start_param(rest):
    """History with start= returns entries after that time."""
    entity = "sensor.hist_param_start"
    await rest.set_state(entity, "v1")
    await asyncio.sleep(_FLUSH)

    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=1)).isoformat()

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}?start={start}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_history_with_start_and_end(rest):
    """History with start= and end= returns bounded entries."""
    entity = "sensor.hist_param_range"
    await rest.set_state(entity, "r1")
    await asyncio.sleep(_FLUSH)

    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_history_narrow_window(rest):
    """History with very narrow window may return fewer entries."""
    entity = "sensor.hist_param_narrow"
    await rest.set_state(entity, "n1")
    await asyncio.sleep(_FLUSH)

    # Very old window that shouldn't contain our data
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).isoformat()
    end = (now - timedelta(days=29)).isoformat()

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}?start={start}&end={end}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0  # No data from 29 days ago


async def test_history_entity_has_all_fields(rest):
    """History entries include entity_id, state, attributes, when."""
    entity = "sensor.hist_param_fields"
    await rest.set_state(entity, "42", {"unit": "C"})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{entity}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    entry = data[0]
    assert "entity_id" in entry
    assert "state" in entry
    assert "attributes" in entry
    assert "last_changed" in entry


async def test_history_nonexistent_entity(rest):
    """History for nonexistent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nonexistent_hist_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []
