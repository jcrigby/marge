"""
CTS -- History Entry Detail Depth Tests

Tests the detailed format of GET /api/history/period/{entity_id}
responses: field presence, attribute recording, same-state recording,
chronological ordering, unknown entity handling, and attribute
mutation tracking across history entries.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.15  # recorder coalesce window


# ── Entry Field Format ────────────────────────────────────

async def test_history_entry_has_entity_id(rest):
    """History entries include entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_eid_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert len(entries) >= 1
    assert entries[0]["entity_id"] == eid


async def test_history_entry_has_state(rest):
    """History entries include state field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_state_{tag}"
    await rest.set_state(eid, "hello")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert entries[-1]["state"] == "hello"


async def test_history_entry_has_last_changed(rest):
    """History entries include last_changed timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_lc_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert "last_changed" in entries[0]
    assert len(entries[0]["last_changed"]) > 0


async def test_history_entry_has_last_updated(rest):
    """History entries include last_updated timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_lu_{tag}"
    await rest.set_state(eid, "42")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert "last_updated" in entries[0]


async def test_history_entry_has_attributes(rest):
    """History entries include attributes object."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_attrs_{tag}"
    await rest.set_state(eid, "72", {"unit": "F"})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    assert "attributes" in entries[-1]
    assert entries[-1]["attributes"]["unit"] == "F"


async def test_history_response_is_array(rest):
    """GET /api/history/period/{eid} returns a JSON array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_arr_{tag}"
    await rest.set_state(eid, "1")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Attribute Mutation Tracking ───────────────────────────

async def test_history_records_attribute_changes(rest):
    """Different attribute values are recorded in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_amut_{tag}"
    await rest.set_state(eid, "on", {"brightness": 100})
    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "on", {"brightness": 200})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    brightness_values = [e["attributes"].get("brightness") for e in entries]
    assert 100 in brightness_values
    assert 200 in brightness_values


async def test_history_records_same_state_updates(rest):
    """Same state value but different writes are recorded."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_same_{tag}"
    await rest.set_state(eid, "constant")
    await asyncio.sleep(_FLUSH)
    await rest.set_state(eid, "constant")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    # At least 2 entries even though state didn't change
    assert len(entries) >= 2


async def test_history_multiple_attrs_preserved(rest):
    """History preserves all attributes, not just a subset."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_mattr_{tag}"
    attrs = {"unit": "W", "friendly_name": f"Power {tag}", "icon": "mdi:flash"}
    await rest.set_state(eid, "1500", attrs)
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    last_attrs = entries[-1]["attributes"]
    assert last_attrs["unit"] == "W"
    assert last_attrs["friendly_name"] == f"Power {tag}"
    assert last_attrs["icon"] == "mdi:flash"


# ── Chronological Ordering ────────────────────────────────

async def test_history_entries_chronological(rest):
    """History entries are in ascending chronological order."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_chrono_{tag}"
    for v in ["10", "20", "30", "40"]:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    timestamps = [e["last_changed"] for e in entries]
    assert timestamps == sorted(timestamps)


async def test_history_state_sequence_preserved(rest):
    """History preserves the exact sequence of state values."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_seq_{tag}"
    sequence = ["A", "B", "C", "D"]
    for v in sequence:
        await rest.set_state(eid, v)
        await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    # All values present in order
    for i, v in enumerate(sequence):
        assert v in states
    # Check ordering: index of A < B < C < D
    indices = [states.index(v) for v in sequence]
    assert indices == sorted(indices)


# ── Unknown Entity ────────────────────────────────────────

async def test_history_unknown_entity_empty(rest):
    """History for a never-created entity returns empty array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.hd_unknown_{tag}"

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []
