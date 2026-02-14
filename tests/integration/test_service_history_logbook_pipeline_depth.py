"""
CTS -- Service → History → Logbook Pipeline Depth Tests

Tests the full pipeline: service call creates state change, which
appears in history, and shows up in logbook with correct fields.
Verifies end-to-end data flow from service through persistence.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Service → History ────────────────────────────────────

async def test_service_state_in_history(rest):
    """State change from service call appears in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pipe_hist_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "on" in states


async def test_service_attrs_in_history(rest):
    """Attributes from service call appear in history entry."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pipe_attr_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 255,
    })
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    on_entry = next((e for e in entries if e["state"] == "on"), None)
    assert on_entry is not None
    assert on_entry["attributes"]["brightness"] == 255


async def test_multiple_services_in_history(rest):
    """Multiple service calls all appear in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.pipe_multi_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 3


# ── Service → Logbook ────────────────────────────────────

async def test_service_state_in_logbook(rest):
    """State change from service call appears in entity logbook."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pipe_lb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "on" in states


async def test_service_in_global_logbook(rest):
    """Service state change appears in global logbook."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.pipe_glb_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    entries = resp.json()
    eids = {e["entity_id"] for e in entries}
    assert eid in eids


async def test_logbook_entry_has_when(rest):
    """Logbook entries from service calls have 'when' field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.pipe_when_{tag}"
    await rest.set_state(eid, "off")
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert "when" in entries[-1]


# ── History + Logbook Consistency ────────────────────────

async def test_history_and_logbook_same_states(rest):
    """History and logbook show the same state values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_cons_{tag}"
    values = ["10", "20", "30"]
    for v in values:
        await rest.set_state(eid, v)
    await asyncio.sleep(0.3)

    hist_resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    hist_states = {e["state"] for e in hist_resp.json()}

    lb_resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    lb_states = {e["state"] for e in lb_resp.json()}

    for v in values:
        assert v in hist_states
        assert v in lb_states


# ── Toggle Sequence in History ───────────────────────────

async def test_toggle_sequence_in_history(rest):
    """Toggle sequence alternates state in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.pipe_tog_{tag}"
    await rest.set_state(eid, "off")
    for _ in range(4):
        await rest.call_service("switch", "toggle", {"entity_id": eid})
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    # Should alternate between on and off
    states = [e["state"] for e in entries]
    assert "on" in states
    assert "off" in states


# ── Delete Doesn't Erase History ─────────────────────────

async def test_delete_entity_history_preserved(rest):
    """Deleting entity doesn't erase its history entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.pipe_delhist_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    await asyncio.sleep(0.3)

    # Delete the entity
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    # History should still have entries
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 2
