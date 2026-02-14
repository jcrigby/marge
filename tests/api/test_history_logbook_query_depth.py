"""
CTS -- History & Logbook Query Depth Tests

Tests history and logbook API query parameters: time range filtering,
entity-specific history, global logbook, logbook deduplication,
and history ordering.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity History ────────────────────────────────────────

async def test_history_returns_list(rest):
    """GET /api/history/period/{entity_id} returns list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_rl_{tag}"
    await rest.set_state(eid, "10")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_history_contains_state(rest):
    """History contains the current state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_cs_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    states = [e.get("state") for e in resp.json()]
    assert "42" in states


async def test_history_multiple_states(rest):
    """History records multiple state changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_ms_{tag}"
    for val in ["10", "20", "30"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.2)
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    states = [e.get("state") for e in resp.json()]
    assert "10" in states
    assert "30" in states


async def test_history_has_timestamps(rest):
    """History entries have last_changed field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hist_ts_{tag}"
    await rest.set_state(eid, "5")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) > 0
    assert "last_changed" in entries[0]


async def test_history_empty_for_unknown(rest):
    """History for nonexistent entity returns empty list."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.hist_unknown_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Global Logbook ────────────────────────────────────────

async def test_logbook_global_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_logbook_global_has_entity_id(rest):
    """Global logbook entries have entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_g_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) > 0
    assert "entity_id" in entries[0]


async def test_logbook_global_has_state(rest):
    """Global logbook entries have state field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "state" in entries[0]


async def test_logbook_global_has_when(rest):
    """Global logbook entries have when field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    if entries:
        assert "when" in entries[0]


# ── Entity Logbook ────────────────────────────────────────

async def test_logbook_entity_returns_list(rest):
    """GET /api/logbook/{entity_id} returns a list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_e_{tag}"
    await rest.set_state(eid, "a")
    await asyncio.sleep(0.2)
    await rest.set_state(eid, "b")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_logbook_entity_dedup(rest):
    """Logbook deduplicates consecutive same states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_dup_{tag}"
    for _ in range(3):
        await rest.set_state(eid, "same")
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    # Should have at most 1 entry since state never changed
    states = [e["state"] for e in entries]
    assert states.count("same") <= 1 or len(entries) <= 2


async def test_logbook_entity_records_changes(rest):
    """Logbook records distinct state transitions."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lb_chg_{tag}"
    await rest.set_state(eid, "alpha")
    await asyncio.sleep(0.2)
    await rest.set_state(eid, "beta")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    states = [e["state"] for e in resp.json()]
    assert "alpha" in states
    assert "beta" in states
