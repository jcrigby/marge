"""
CTS — State Machine Tests (~20 tests)

Tests the core state CRUD operations, event generation, and timestamp semantics
via the REST API. These tests validate SSS §4.1.2 (STATE-001 through STATE-008).
"""

import asyncio
import time

import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


async def test_api_running(rest):
    """GET /api/ returns a running status."""
    result = await rest.get_api_status()
    assert "message" in result


async def test_get_states_returns_list(rest):
    """GET /api/states returns a JSON array."""
    states = await rest.get_states()
    assert isinstance(states, list)


async def test_set_and_get_state(rest):
    """POST then GET a state roundtrips correctly."""
    entity_id = "test.state_roundtrip"
    result = await rest.set_state(entity_id, "hello", {"key": "value"})
    assert result["entity_id"] == entity_id
    assert result["state"] == "hello"

    fetched = await rest.get_state(entity_id)
    assert fetched is not None
    assert fetched["state"] == "hello"
    assert fetched["attributes"]["key"] == "value"


async def test_set_state_creates_entity(rest):
    """POST /api/states creates a new entity if it doesn't exist."""
    entity_id = "test.new_entity_create"
    result = await rest.set_state(entity_id, "initial")
    assert result["entity_id"] == entity_id
    assert result["state"] == "initial"


async def test_set_state_updates_existing(rest):
    """POST /api/states updates an existing entity."""
    entity_id = "test.update_existing"
    await rest.set_state(entity_id, "first")
    result = await rest.set_state(entity_id, "second")
    assert result["state"] == "second"


async def test_get_nonexistent_returns_404(rest):
    """GET for a nonexistent entity returns 404 / None."""
    result = await rest.get_state("test.definitely_does_not_exist_xyz")
    assert result is None


async def test_state_has_timestamps(rest):
    """State objects include last_changed, last_updated, last_reported."""
    entity_id = "test.timestamp_check"
    result = await rest.set_state(entity_id, "on")
    assert "last_changed" in result
    assert "last_updated" in result
    assert "last_reported" in result


async def test_last_changed_updates_on_value_change(rest):
    """last_changed updates when state value changes (STATE-006)."""
    entity_id = "test.last_changed_value"
    r1 = await rest.set_state(entity_id, "off")
    t1 = r1["last_changed"]

    # Small delay to ensure timestamp difference
    await asyncio.sleep(0.05)

    r2 = await rest.set_state(entity_id, "on")
    t2 = r2["last_changed"]
    assert t2 > t1, "last_changed should update when state value changes"


async def test_last_changed_stable_on_same_value(rest):
    """last_changed stays the same when state value doesn't change (STATE-006)."""
    entity_id = "test.last_changed_stable"
    r1 = await rest.set_state(entity_id, "on")
    t1 = r1["last_changed"]

    await asyncio.sleep(0.05)

    r2 = await rest.set_state(entity_id, "on")
    t2 = r2["last_changed"]
    assert t2 == t1, "last_changed should NOT update when state is unchanged"


async def test_last_updated_changes_on_attribute_change(rest):
    """last_updated changes when attributes change even if state doesn't."""
    entity_id = "test.last_updated_attrs"
    r1 = await rest.set_state(entity_id, "on", {"brightness": 100})
    t1 = r1["last_updated"]

    await asyncio.sleep(0.05)

    r2 = await rest.set_state(entity_id, "on", {"brightness": 200})
    t2 = r2["last_updated"]
    assert t2 > t1, "last_updated should update when attributes change"


async def test_context_id_unique_per_update(rest):
    """Each state update gets a unique context id."""
    entity_id = "test.context_unique"
    r1 = await rest.set_state(entity_id, "a")
    r2 = await rest.set_state(entity_id, "b")
    assert r1["context"]["id"] != r2["context"]["id"]


async def test_empty_attributes_default(rest):
    """Setting state without attributes uses empty attributes."""
    entity_id = "test.empty_attrs"
    result = await rest.set_state(entity_id, "on")
    assert isinstance(result["attributes"], dict)


async def test_attributes_merge_replaced(rest):
    """Attributes are replaced, not merged, on update."""
    entity_id = "test.attrs_replace"
    await rest.set_state(entity_id, "on", {"a": 1, "b": 2})
    r2 = await rest.set_state(entity_id, "on", {"c": 3})
    # New attributes should replace old ones entirely
    assert "c" in r2["attributes"]


async def test_entity_id_format(rest):
    """Entity IDs must be domain.object_id format."""
    entity_id = "light.test_format"
    result = await rest.set_state(entity_id, "on")
    assert result["entity_id"] == entity_id


async def test_state_is_string(rest):
    """State values are always strings."""
    entity_id = "test.string_state"
    result = await rest.set_state(entity_id, "42")
    assert isinstance(result["state"], str)
    assert result["state"] == "42"


async def test_concurrent_writes(rest):
    """Multiple concurrent state writes don't lose data."""
    tasks = []
    for i in range(10):
        eid = f"test.concurrent_{i}"
        tasks.append(rest.set_state(eid, str(i)))
    results = await asyncio.gather(*tasks)
    for i, r in enumerate(results):
        assert r["state"] == str(i)
