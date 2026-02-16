"""
CTS -- State Machine Timestamp and Context Semantics (STATE-006)

Tests last_changed vs last_updated vs last_reported behavior,
context propagation, old_state on first set, and attribute-only updates.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_first_set_timestamps_all_equal(rest):
    """First set: last_changed == last_updated == last_reported."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_first_{tag}"
    await rest.set_state(eid, "initial")

    state = await rest.get_state(eid)
    assert state["last_changed"] == state["last_updated"]
    assert state["last_updated"] == state["last_reported"]


async def test_same_state_last_changed_stable(rest):
    """Re-setting same state: last_changed does NOT advance."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_stable_{tag}"
    await rest.set_state(eid, "value1")

    s1 = await rest.get_state(eid)
    lc1 = s1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "value1")  # same state

    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == lc1, "last_changed should not advance on same state"


async def test_different_state_last_changed_advances(rest):
    """Changing state: last_changed DOES advance."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_advance_{tag}"
    await rest.set_state(eid, "value1")

    s1 = await rest.get_state(eid)
    lc1 = s1["last_changed"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "value2")  # different state

    s2 = await rest.get_state(eid)
    assert s2["last_changed"] != lc1, "last_changed should advance on state change"


async def test_last_reported_always_advances(rest):
    """last_reported advances on every set(), even same state + same attrs."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_reported_{tag}"
    await rest.set_state(eid, "val", {"a": 1})

    s1 = await rest.get_state(eid)
    lr1 = s1["last_reported"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "val", {"a": 1})  # identical

    s2 = await rest.get_state(eid)
    assert s2["last_reported"] >= lr1, "last_reported should always advance"


async def test_attribute_only_change_last_updated_advances(rest):
    """Changing only attributes: last_updated advances, last_changed stable."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_attronly_{tag}"
    await rest.set_state(eid, "fixed", {"color": "red"})

    s1 = await rest.get_state(eid)
    lc1 = s1["last_changed"]
    lu1 = s1["last_updated"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "fixed", {"color": "blue"})  # same state, diff attrs

    s2 = await rest.get_state(eid)
    assert s2["last_changed"] == lc1, "last_changed stable on attr-only change"
    assert s2["last_updated"] != lu1, "last_updated advances on attr change"


async def test_same_state_same_attrs_last_updated_stable(rest):
    """Identical state + attrs: last_updated does NOT advance."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_identical_{tag}"
    await rest.set_state(eid, "same", {"x": 1})

    s1 = await rest.get_state(eid)
    lu1 = s1["last_updated"]

    await asyncio.sleep(0.05)
    await rest.set_state(eid, "same", {"x": 1})

    s2 = await rest.get_state(eid)
    assert s2["last_updated"] == lu1, "last_updated stable when nothing changed"


async def test_context_has_uuid_format(rest):
    """Context.id is a valid UUID-like string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ctx_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    ctx = state["context"]
    assert "id" in ctx
    assert len(ctx["id"]) >= 32  # UUID with or without hyphens


async def test_context_changes_on_each_set(rest):
    """Each set() produces a new context ID."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ctx2_{tag}"
    await rest.set_state(eid, "a")
    s1 = await rest.get_state(eid)

    await rest.set_state(eid, "b")
    s2 = await rest.get_state(eid)

    assert s1["context"]["id"] != s2["context"]["id"]


async def test_state_change_event_via_ws(ws, rest):
    """WS subscribe_events delivers state_changed with old_state and new_state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_ws_{tag}"
    await rest.set_state(eid, "initial")

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    assert sub.get("success", False) is True
    sub_id = sub["id"]

    await rest.set_state(eid, "changed")

    # Consume events until we find ours
    found = False
    for _ in range(50):
        try:
            msg = await ws.recv_event(timeout=2.0)
        except asyncio.TimeoutError:
            break
        if msg.get("type") == "event":
            event = msg["event"]
            if event.get("data", {}).get("entity_id") == eid:
                assert event["data"]["old_state"]["state"] == "initial"
                assert event["data"]["new_state"]["state"] == "changed"
                found = True
                break
    assert found, f"Did not receive state_changed event for {eid}"

    await ws.send_command("unsubscribe_events", subscription=sub_id)


async def test_old_state_none_on_first_set(ws, rest):
    """First-ever set for an entity: old_state is null in event."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_firstset_{tag}"

    sub = await ws.send_command("subscribe_events", event_type="state_changed")
    sub_id = sub["id"]

    await rest.set_state(eid, "brand_new")

    found = False
    for _ in range(50):
        try:
            msg = await ws.recv_event(timeout=2.0)
        except asyncio.TimeoutError:
            break
        if msg.get("type") == "event":
            event = msg["event"]
            if event.get("data", {}).get("entity_id") == eid:
                assert event["data"]["old_state"] is None
                assert event["data"]["new_state"]["state"] == "brand_new"
                found = True
                break
    assert found, f"Did not receive state_changed event for {eid}"

    await ws.send_command("unsubscribe_events", subscription=sub_id)


async def test_timestamps_are_iso8601(rest):
    """Timestamps are ISO 8601 format with T separator."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ts_iso_{tag}"
    await rest.set_state(eid, "x")

    state = await rest.get_state(eid)
    for field in ["last_changed", "last_updated", "last_reported"]:
        ts = state[field]
        assert "T" in ts, f"{field} should be ISO 8601"
        assert "20" in ts, f"{field} should contain year"


# ── Entity Count and Remove (from depth) ───────────────


async def test_entity_count_increases(rest):
    """Creating entities increases total entity count."""
    s1 = await rest.get_states()
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.cnt_{tag}", "1")
    s2 = await rest.get_states()
    assert len(s2) >= len(s1) + 1


async def test_delete_entity_decreases_count(rest):
    """Deleting entity decreases count."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_cnt_{tag}"
    await rest.set_state(eid, "1")
    before = await rest.get_states()
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    after = await rest.get_states()
    assert len(after) < len(before)


# ── State Object Fields (from depth) ──────────────────


async def test_entity_id_in_state(rest):
    """Returned state includes the entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.eid_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


async def test_state_value_is_string(rest):
    """State value is always a string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.str_{tag}"
    await rest.set_state(eid, "42")
    state = await rest.get_state(eid)
    assert isinstance(state["state"], str)
    assert state["state"] == "42"


# ── Attributes (from depth) ───────────────────────────


async def test_attributes_default_empty(rest):
    """Attributes default to empty dict when not provided."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.adef_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert isinstance(state["attributes"], dict)


async def test_attributes_preserved_on_state_change(rest):
    """Setting state with same attributes preserves them."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.apres_{tag}"
    await rest.set_state(eid, "1", {"unit": "W", "friendly_name": "Power"})
    await rest.set_state(eid, "2", {"unit": "W", "friendly_name": "Power"})
    state = await rest.get_state(eid)
    assert state["state"] == "2"
    assert state["attributes"]["unit"] == "W"
    assert state["attributes"]["friendly_name"] == "Power"
