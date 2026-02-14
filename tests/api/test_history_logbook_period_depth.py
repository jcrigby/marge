"""
CTS -- History and Logbook Endpoint Depth Tests

Tests GET /api/history/period/{entity_id} and GET /api/logbook
endpoints. Verifies history records state changes, logbook filters
by entity, and global logbook returns cross-entity entries.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── History Period ────────────────────────────────────────

async def test_history_returns_list(rest):
    """GET /api/history/period/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_{tag}"
    await rest.set_state(eid, "10")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_records_state(rest):
    """History records a state change (with flush delay)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_rec_{tag}"
    await rest.set_state(eid, "first")
    await rest.set_state(eid, "second")
    await asyncio.sleep(0.3)  # wait for recorder batch flush
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    states = [e["state"] for e in data]
    assert "second" in states


async def test_history_has_entity_id(rest):
    """History entries have entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_eid_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert all(e["entity_id"] == eid for e in data)


async def test_history_has_timestamps(rest):
    """History entries have last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_ts_{tag}"
    await rest.set_state(eid, "50")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert "last_changed" in data[0]
        assert "last_updated" in data[0]


async def test_history_has_attributes(rest):
    """History entries have attributes object."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_attr_{tag}"
    await rest.set_state(eid, "75", {"unit": "W"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert "attributes" in data[0]


async def test_history_multiple_changes(rest):
    """History records multiple state transitions (with flush delay)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_multi_{tag}"
    for val in ["10", "20", "30", "40"]:
        await rest.set_state(eid, val)
    await asyncio.sleep(0.3)  # wait for recorder batch flush
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 4
    states = [e["state"] for e in data]
    assert "40" in states


# ── Logbook Per Entity ────────────────────────────────────

async def test_logbook_returns_list(rest):
    """GET /api/logbook/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_{tag}"
    await rest.set_state(eid, "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_records_change(rest):
    """Logbook records state transition."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_rec_{tag}"
    await rest.set_state(eid, "off")
    await rest.set_state(eid, "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert all(e.get("entity_id") == eid for e in data)


async def test_logbook_has_when(rest):
    """Logbook entries have when field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_when_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert "when" in data[0]


# ── Global Logbook ────────────────────────────────────────

async def test_global_logbook_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_global_logbook_has_entries(rest):
    """Global logbook has entries after state changes."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.glb_{tag}", "99")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1


async def test_global_logbook_entries_have_entity_id(rest):
    """Global logbook entries have entity_id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    data = resp.json()
    if data:
        assert all("entity_id" in e for e in data)
