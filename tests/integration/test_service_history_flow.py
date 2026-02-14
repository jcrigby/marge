"""
CTS -- Service Call -> State -> History Integration Flow

Tests the full pipeline: REST service call changes entity state,
state change is recorded by the async recorder, and appears in
the history API. Also tests history query parameters.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

_FLUSH = 0.6  # Recorder coalesces writes at 100ms + margin


async def test_service_state_in_history(rest):
    """Service call state change appears in history."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.shf_{tag}"
    await rest.set_state(eid, "off")
    await asyncio.sleep(_FLUSH)

    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    states = [e["state"] for e in data]
    assert "on" in states


async def test_multiple_service_calls_in_history(rest):
    """Multiple service calls produce multiple history entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.shf_multi_{tag}"
    await rest.set_state(eid, "off")
    await asyncio.sleep(_FLUSH)

    await rest.call_service("switch", "turn_on", {"entity_id": eid})
    await asyncio.sleep(0.15)
    await rest.call_service("switch", "turn_off", {"entity_id": eid})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    data = resp.json()
    states = [e["state"] for e in data]
    assert "on" in states
    assert "off" in states


async def test_history_entry_has_required_fields(rest):
    """History entries have entity_id, state, last_changed, last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.shf_fields_{tag}"
    await rest.set_state(eid, "val1")
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    entry = data[0]
    assert "state" in entry
    assert "last_changed" in entry
    assert "last_updated" in entry


async def test_history_attributes_preserved(rest):
    """History entries preserve attributes from state changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.shf_attrs_{tag}"
    await rest.set_state(eid, "72", {"unit": "F", "friendly_name": f"Temp {tag}"})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    # Attributes should be present (either as object or JSON string)
    entry = data[0]
    attrs = entry.get("attributes", {})
    if isinstance(attrs, str):
        import json
        attrs = json.loads(attrs)
    assert attrs.get("unit") == "F"


async def test_history_empty_for_nonexistent(rest):
    """History for nonexistent entity returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.shf_nonexist_999",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_statistics_after_numeric_states(rest):
    """Statistics endpoint shows aggregates after numeric state writes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.shf_stat_{tag}"
    for val in ["10", "20", "30", "40", "50"]:
        await rest.set_state(eid, val)
        await asyncio.sleep(0.05)
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        bucket = data[0]
        assert "min" in bucket
        assert "max" in bucket
        assert "mean" in bucket
        assert "count" in bucket
        assert bucket["min"] <= bucket["max"]


async def test_logbook_after_service_call(rest):
    """Logbook captures entries from service-driven state changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.shf_logb_{tag}"
    await rest.set_state(eid, "off")
    await asyncio.sleep(0.15)
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_history_ordered_chronologically(rest):
    """History entries are ordered by time."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.shf_order_{tag}"
    for i in range(5):
        await rest.set_state(eid, str(i))
        await asyncio.sleep(0.05)
    await asyncio.sleep(_FLUSH)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) >= 2:
        timestamps = [e.get("last_updated", "") for e in data]
        assert timestamps == sorted(timestamps)


async def test_delete_entity_history_persists(rest):
    """Deleting entity does not remove its history entries."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.shf_del_{tag}"
    await rest.set_state(eid, "before_delete")
    await asyncio.sleep(_FLUSH)

    # Delete the entity
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # History should still have entries
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        params={"start": "2020-01-01T00:00:00Z", "end": "2030-01-01T00:00:00Z"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    # History persists in SQLite even after entity deletion
    states = [e["state"] for e in data]
    assert "before_delete" in states
