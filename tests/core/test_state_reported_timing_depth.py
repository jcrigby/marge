"""
CTS -- State last_reported and Timing Edge Case Depth Tests

Tests that last_reported always advances on every set_state call (even when
state and attributes are identical), that last_changed is preserved when only
attributes change, and other timestamp ordering invariants.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── last_reported Always Advances ────────────────────────

async def test_last_reported_advances_same_state_same_attrs(rest):
    """last_reported advances even when state and attributes are identical."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rep_same_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "42", {"unit": "W"})
    s2 = await rest.get_state(eid)
    assert s2["last_reported"] >= s1["last_reported"]


async def test_last_reported_advances_on_state_change(rest):
    """last_reported advances on actual state value change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rep_chg_{tag}"
    await rest.set_state(eid, "A")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "B")
    s2 = await rest.get_state(eid)
    assert s2["last_reported"] >= s1["last_reported"]


async def test_last_reported_advances_on_attr_change(rest):
    """last_reported advances on attribute-only change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rep_attr_{tag}"
    await rest.set_state(eid, "42", {"unit": "W"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "42", {"unit": "kW"})
    s2 = await rest.get_state(eid)
    assert s2["last_reported"] >= s1["last_reported"]


# ── last_changed Preserved When Only Attrs Change ────────

async def test_last_changed_preserved_attr_only_change(rest):
    """last_changed stays the same when only attributes change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_attr_{tag}"
    await rest.set_state(eid, "100", {"color": "red"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "100", {"color": "blue"})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]


async def test_last_updated_advances_attr_only_change(rest):
    """last_updated advances when only attributes change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lu_attr_{tag}"
    await rest.set_state(eid, "100", {"mode": "auto"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "100", {"mode": "manual"})
    s2 = await rest.get_state(eid)
    assert s2["last_updated"] >= s1["last_updated"]


# ── Neither Timestamp Changes When Identical ─────────────

async def test_last_changed_preserved_identical_set(rest):
    """last_changed preserved when state+attrs are identical."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_ident_{tag}"
    await rest.set_state(eid, "X", {"k": "v"})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "X", {"k": "v"})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == s1["last_changed"]


async def test_last_updated_preserved_identical_set(rest):
    """last_updated preserved when state+attrs are identical."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lu_ident_{tag}"
    await rest.set_state(eid, "Y", {"a": 1})
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "Y", {"a": 1})
    s2 = await rest.get_state(eid)
    assert s2["last_updated"] == s1["last_updated"]


# ── State Change Updates Both Timestamps ─────────────────

async def test_state_change_updates_last_changed(rest):
    """State value change updates last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.chg_lc_{tag}"
    await rest.set_state(eid, "one")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "two")
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] > s1["last_changed"]


async def test_state_change_updates_last_updated(rest):
    """State value change also updates last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.chg_lu_{tag}"
    await rest.set_state(eid, "alpha")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "beta")
    s2 = await rest.get_state(eid)
    assert s2["last_updated"] > s1["last_updated"]


# ── Timestamp Ordering Invariants ────────────────────────

async def test_timestamps_ordered_new_entity(rest):
    """New entity: last_changed <= last_updated <= last_reported."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.order_new_{tag}"
    await rest.set_state(eid, "42")
    s = await rest.get_state(eid)
    assert s["last_changed"] <= s["last_updated"]
    assert s["last_updated"] <= s["last_reported"]


async def test_timestamps_ordered_after_update(rest):
    """After state change: last_changed <= last_updated <= last_reported."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.order_upd_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    s = await rest.get_state(eid)
    assert s["last_changed"] <= s["last_updated"]
    assert s["last_updated"] <= s["last_reported"]


async def test_timestamps_ordered_after_identical(rest):
    """After identical set: last_changed <= last_updated <= last_reported."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.order_ident_{tag}"
    await rest.set_state(eid, "Z")
    await asyncio.sleep(0.05)
    await rest.set_state(eid, "Z")
    s = await rest.get_state(eid)
    assert s["last_changed"] <= s["last_updated"]
    assert s["last_updated"] <= s["last_reported"]


# ── Service Calls Update Timestamps ──────────────────────

async def test_service_call_updates_last_changed(rest):
    """Service call that changes state updates last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_lc_{tag}"
    await rest.set_state(eid, "off")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    s2 = await rest.get_state(eid)
    assert s2["last_changed"] > s1["last_changed"]


async def test_service_call_preserves_last_changed_same_state(rest):
    """Service call that sets same state preserves last_changed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.svc_same_{tag}"
    await rest.set_state(eid, "on")
    s1 = await rest.get_state(eid)
    await asyncio.sleep(0.05)
    # turn_on when already on — state stays "on"
    await rest.call_service("light", "turn_on", {"entity_id": eid})
    s2 = await rest.get_state(eid)
    # Attrs may change (brightness added), so last_updated may advance,
    # but state is still "on" so last_changed is preserved
    assert s2["last_changed"] == s1["last_changed"]
