"""
CTS -- Device Tracker & Input Datetime Services Depth Tests

Tests device_tracker.see service and input_datetime.set_datetime
service with attribute handling.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Device Tracker ──────────────────────────────────────

async def test_device_tracker_see_home(rest):
    """device_tracker.see sets location_name = home → state home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dtid_home_{tag}"
    await rest.set_state(eid, "not_home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "home",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "home"


async def test_device_tracker_see_away(rest):
    """device_tracker.see sets location_name = not_home."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dtid_away_{tag}"
    await rest.set_state(eid, "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "not_home",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "not_home"


async def test_device_tracker_see_custom_location(rest):
    """device_tracker.see with custom location."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dtid_cust_{tag}"
    await rest.set_state(eid, "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "office",
    })
    state = await rest.get_state(eid)
    assert state["state"] == "office"


async def test_device_tracker_see_sets_gps(rest):
    """device_tracker.see with GPS stores latitude/longitude."""
    tag = uuid.uuid4().hex[:8]
    eid = f"device_tracker.dtid_gps_{tag}"
    await rest.set_state(eid, "home")
    await rest.call_service("device_tracker", "see", {
        "entity_id": eid,
        "location_name": "home",
        "gps": [40.7, -74.0],
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["gps"] == [40.7, -74.0]


# ── Input Datetime ──────────────────────────────────────

async def test_input_datetime_set_datetime(rest):
    """input_datetime.set_datetime sets state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dtid_dt_{tag}"
    await rest.set_state(eid, "00:00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "datetime": "2024-06-15 14:30:00",
    })
    state = await rest.get_state(eid)
    assert "14:30" in state["state"] or "2024-06-15" in state["state"]


async def test_input_datetime_set_time(rest):
    """input_datetime.set_datetime with time only."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dtid_time_{tag}"
    await rest.set_state(eid, "00:00:00")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "time": "08:30:00",
    })
    state = await rest.get_state(eid)
    assert "08:30" in state["state"]


async def test_input_datetime_set_date(rest):
    """input_datetime.set_datetime with date only."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dtid_date_{tag}"
    await rest.set_state(eid, "2000-01-01")
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "date": "2024-12-25",
    })
    state = await rest.get_state(eid)
    assert "2024-12-25" in state["state"]


async def test_input_datetime_preserves_attrs(rest):
    """input_datetime.set_datetime preserves attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"input_datetime.dtid_attr_{tag}"
    await rest.set_state(eid, "12:00:00", {"has_date": False, "has_time": True})
    await rest.call_service("input_datetime", "set_datetime", {
        "entity_id": eid,
        "time": "15:45:00",
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["has_time"] is True
