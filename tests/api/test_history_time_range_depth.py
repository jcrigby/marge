"""
CTS -- History Time Range Query Depth Tests

Tests history endpoint with start/end parameters, boundary conditions,
and time-filtered logbook queries.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic History Range ──────────────────────────────────

async def test_history_default_range(rest):
    """History without params returns recent entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_{tag}"
    await rest.set_state(eid, "10")
    await rest.set_state(eid, "20")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_history_with_start_param(rest):
    """History with start param returns entries after start."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_s_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    await asyncio.sleep(0.3)
    # Use a very early start to get all entries
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start=2000-01-01T00:00:00Z",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


async def test_history_with_future_start(rest):
    """History with future start returns empty."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_fs_{tag}"
    await rest.set_state(eid, "X")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?start=2099-01-01T00:00:00Z",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


async def test_history_with_past_end(rest):
    """History with past end returns empty (entries after end cutoff)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_pe_{tag}"
    await rest.set_state(eid, "Y")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}?end=2000-01-01T00:00:00Z",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0


# ── Logbook Time Range ───────────────────────────────────

async def test_logbook_default_range(rest):
    """Global logbook without params returns recent entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lb_{tag}"
    await rest.set_state(eid, "started")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_logbook_entity_range(rest):
    """Entity logbook returns entries for specific entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lbe_{tag}"
    await rest.set_state(eid, "on")
    await rest.set_state(eid, "off")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 2
    for e in entries:
        assert e["entity_id"] == eid


async def test_logbook_entity_with_start(rest):
    """Entity logbook with start param returns filtered entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lbs_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}?start=2000-01-01T00:00:00Z",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── History Entry Format ─────────────────────────────────

async def test_history_entry_has_state(rest):
    """History entry has state field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_fmt_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "state" in entries[0]
    assert entries[0]["state"] == "42"


async def test_history_entry_has_last_changed(rest):
    """History entry has last_changed timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lc_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "last_changed" in entries[0]


async def test_history_entry_has_attributes(rest):
    """History entry has attributes field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_at_{tag}"
    await rest.set_state(eid, "50", {"unit": "dB"})
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    attrs = entries[-1].get("attributes", {})
    # Attributes may be JSON string or dict
    if isinstance(attrs, str):
        import json
        attrs = json.loads(attrs)
    assert attrs.get("unit") == "dB"


# ── Logbook Entry Format ────────────────────────────────

async def test_logbook_entry_has_when(rest):
    """Logbook entry has 'when' timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lbw_{tag}"
    await rest.set_state(eid, "active")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "when" in entries[0]


async def test_logbook_entry_has_entity_and_state(rest):
    """Logbook entry has entity_id and state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.htr_lbes_{tag}"
    await rest.set_state(eid, "triggered")
    await asyncio.sleep(0.3)
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert entries[0]["entity_id"] == eid
    assert entries[0]["state"] == "triggered"
