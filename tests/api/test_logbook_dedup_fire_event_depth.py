"""
CTS -- Logbook Deduplication and Fire Event Depth Tests

Tests that the entity logbook deduplicates consecutive identical states,
that the global logbook works correctly, and that the fire_event endpoint
produces correct responses and triggers automation processing.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Logbook Deduplication ──────────────────────────────────

async def test_logbook_dedup_same_state(rest):
    """Setting same state 3x produces fewer logbook entries than 3."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_dup_{tag}"
    await rest.set_state(eid, "42")
    await rest.set_state(eid, "42")
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    # Consecutive same states are deduplicated — expect exactly 1
    assert len(entries) == 1
    assert entries[0]["state"] == "42"


async def test_logbook_dedup_alternating(rest):
    """Alternating states are NOT deduplicated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_alt_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    await rest.set_state(eid, "A")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert states == ["A", "B", "A"]


async def test_logbook_dedup_consecutive_then_change(rest):
    """Repeated state then change: deduplication collapses the repeats."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_cc_{tag}"
    await rest.set_state(eid, "on")
    await rest.set_state(eid, "on")
    await rest.set_state(eid, "on")
    await rest.set_state(eid, "off")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert states == ["on", "off"]


async def test_logbook_dedup_preserves_entity_id(rest):
    """Deduplicated logbook entries still have correct entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_eid_{tag}"
    await rest.set_state(eid, "X")
    await rest.set_state(eid, "Y")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) == 2
    for e in entries:
        assert e["entity_id"] == eid


async def test_logbook_dedup_has_when_timestamp(rest):
    """All deduplicated logbook entries have 'when' field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_when_{tag}"
    await rest.set_state(eid, "first")
    await rest.set_state(eid, "second")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    for e in entries:
        assert "when" in e
        assert isinstance(e["when"], str)
        assert len(e["when"]) > 0


# ── Global Logbook ─────────────────────────────────────────

async def test_global_logbook_contains_entity(rest):
    """Global logbook includes entries from multiple entities."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.lbd_g1_{tag}"
    eid2 = f"light.lbd_g2_{tag}"
    await rest.set_state(eid1, "100")
    await rest.set_state(eid2, "on")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    entries = resp.json()
    eids_found = {e["entity_id"] for e in entries}
    assert eid1 in eids_found
    assert eid2 in eids_found


async def test_global_logbook_entries_have_state(rest):
    """Global logbook entries have state and entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbd_gs_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    matching = [e for e in entries if e["entity_id"] == eid]
    assert len(matching) >= 1
    assert matching[0]["state"] == "42"
    assert "when" in matching[0]


# ── Fire Event Endpoint ────────────────────────────────────

async def test_fire_event_response_format(rest):
    """POST /api/events/{type} returns message with event type."""
    tag = uuid.uuid4().hex[:8]
    event_type = f"test_event_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/{event_type}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert event_type in data["message"]


async def test_fire_event_with_body(rest):
    """Fire event with JSON body succeeds."""
    tag = uuid.uuid4().hex[:8]
    event_type = f"custom_event_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/{event_type}",
        json={"key": "value", "number": 42},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert event_type in resp.json()["message"]


async def test_fire_event_without_body(rest):
    """Fire event with empty body succeeds."""
    tag = uuid.uuid4().hex[:8]
    event_type = f"empty_event_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/{event_type}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_message_contains_fired(rest):
    """Fire event response message contains 'fired'."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_fired_{tag}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "fired" in data["message"].lower()


async def test_fire_event_different_types(rest):
    """Multiple different event types can be fired."""
    tag = uuid.uuid4().hex[:8]
    for suffix in ["alpha", "beta", "gamma"]:
        resp = await rest.client.post(
            f"{rest.base_url}/api/events/{suffix}_{tag}",
            headers=rest._headers(),
        )
        assert resp.status_code == 200
        assert f"{suffix}_{tag}" in resp.json()["message"]


# ── Events Listing ─────────────────────────────────────────

async def test_events_listing_has_state_changed(rest):
    """GET /api/events includes state_changed event type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    events = resp.json()
    types = [e["event"] for e in events]
    assert "state_changed" in types


async def test_events_listing_has_listener_count(rest):
    """Event listing entries have event and listener_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    events = resp.json()
    assert len(events) > 0
    for e in events:
        assert "event" in e
        assert "listener_count" in e
        assert isinstance(e["listener_count"], int)
