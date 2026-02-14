"""
CTS -- Logbook Multi-Entity Depth Tests

Tests global logbook behavior with multiple entities: interleaving,
ordering (most recent first), entity_id field in entries, when field
format, and dedup behavior for same-entity consecutive states.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.15


# ── Global Logbook Multi-Entity ──────────────────────────

async def test_global_logbook_contains_multiple_entities(rest):
    """Global logbook includes entries from different entities."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.lme_a_{tag}"
    eid2 = f"switch.lme_b_{tag}"
    await rest.set_state(eid1, "val_a")
    await rest.set_state(eid2, "on")
    await asyncio.sleep(_FLUSH * 2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    eids = {e["entity_id"] for e in entries}
    assert eid1 in eids
    assert eid2 in eids


async def test_global_logbook_most_recent_first(rest):
    """Global logbook entries are ordered most recent first."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    if len(entries) >= 2:
        # When field should be in descending order
        whens = [e["when"] for e in entries]
        assert whens == sorted(whens, reverse=True)


async def test_global_logbook_entry_has_when(rest):
    """Every global logbook entry has a when field."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.lme_when_{tag}", "v")
    await asyncio.sleep(_FLUSH * 2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    for entry in entries:
        assert "when" in entry
        assert len(entry["when"]) > 0


async def test_global_logbook_entry_has_entity_id(rest):
    """Every global logbook entry has entity_id."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    for entry in entries:
        assert "entity_id" in entry


async def test_global_logbook_entry_has_state(rest):
    """Every global logbook entry has state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    for entry in entries:
        assert "state" in entry


# ── Entity Logbook Dedup ──────────────────────────────────

async def test_entity_logbook_dedup_same_state(rest):
    """Entity logbook deduplicates consecutive identical states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lme_dedup_{tag}"
    await rest.set_state(eid, "alpha")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "alpha")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "beta")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    # "alpha" should appear only once due to dedup
    assert states.count("alpha") == 1
    assert "beta" in states


async def test_entity_logbook_shows_transitions(rest):
    """Entity logbook shows state transitions."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lme_trans_{tag}"
    for v in ["A", "B", "C"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "A" in states
    assert "B" in states
    assert "C" in states


async def test_entity_logbook_chronological(rest):
    """Entity logbook entries are in chronological order."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lme_chrono_{tag}"
    for v in ["X", "Y", "Z"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    whens = [e["when"] for e in entries]
    assert whens == sorted(whens)


# ── Logbook After Service Calls ───────────────────────────

async def test_logbook_after_service_call(rest):
    """Service call state change appears in entity logbook."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lme_svc_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(_FLUSH * 2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "on" in states
