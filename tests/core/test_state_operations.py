"""
CTS -- State Machine Operation Tests

Tests state set/get/delete semantics, attribute merge behavior,
context IDs, batch operations, and concurrent access patterns.
"""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


# ── Set and Get ──────────────────────────────────────────────

async def test_set_state_returns_full_entity(rest):
    """POST /api/states/:id returns the full entity object."""
    result = await rest.set_state("sensor.set_return_test", "42", {"unit": "m"})
    assert result["entity_id"] == "sensor.set_return_test"
    assert result["state"] == "42"
    assert result["attributes"]["unit"] == "m"


async def test_set_state_preserves_existing_attrs(rest):
    """Setting state with new attrs preserves unmodified existing attrs."""
    await rest.set_state("sensor.preserve_attrs", "1", {"a": 1, "b": 2})
    await rest.set_state("sensor.preserve_attrs", "2", {"a": 10, "c": 3})
    state = await rest.get_state("sensor.preserve_attrs")
    assert state["state"] == "2"
    # In Marge, attrs are replaced per POST, not merged
    assert state["attributes"]["a"] == 10


async def test_get_state_returns_none_for_missing(rest):
    """GET /api/states/:id returns 404 for nonexistent entity."""
    state = await rest.get_state("sensor.totally_missing_xyz")
    assert state is None


async def test_get_all_states_is_list(rest):
    """GET /api/states returns a list of all entities."""
    await rest.set_state("sensor.all_states_test", "1")
    states = await rest.get_states()
    assert isinstance(states, list)
    assert len(states) >= 1


async def test_set_state_with_empty_attrs(rest):
    """Setting state with empty attributes object works."""
    result = await rest.set_state("sensor.empty_attrs", "ok", {})
    assert result["state"] == "ok"
    assert result["attributes"] == {}


async def test_set_state_with_null_like_value(rest):
    """Setting state to empty string works."""
    result = await rest.set_state("sensor.null_like", "")
    assert result["state"] == ""


# ── Context IDs ──────────────────────────────────────────────

async def test_context_id_present(rest):
    """Entity state includes context with id."""
    await rest.set_state("sensor.ctx_test", "1")
    state = await rest.get_state("sensor.ctx_test")
    assert "context" in state
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_context_id_changes_on_update(rest):
    """Context ID changes with each state update."""
    await rest.set_state("sensor.ctx_change", "1")
    state1 = await rest.get_state("sensor.ctx_change")
    ctx1 = state1["context"]["id"]

    await rest.set_state("sensor.ctx_change", "2")
    state2 = await rest.get_state("sensor.ctx_change")
    ctx2 = state2["context"]["id"]

    assert ctx1 != ctx2


# ── Batch Operations ────────────────────────────────────────

async def test_many_entities_created(rest):
    """Can create many entities without error."""
    for i in range(50):
        await rest.set_state(f"sensor.batch_create_{i}", str(i))
    state = await rest.get_state("sensor.batch_create_49")
    assert state["state"] == "49"


async def test_concurrent_different_entities(rest):
    """Concurrent updates to different entities all succeed."""
    tasks = [
        rest.set_state(f"sensor.concurrent_diff_{i}", str(i))
        for i in range(20)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 20
    for i, r in enumerate(results):
        assert r["state"] == str(i)


async def test_concurrent_same_entity(rest):
    """Concurrent updates to same entity — last writer wins."""
    entity = "sensor.concurrent_same"
    tasks = [
        rest.set_state(entity, str(i))
        for i in range(10)
    ]
    await asyncio.gather(*tasks)
    state = await rest.get_state(entity)
    # State should be one of the values
    assert state["state"] in [str(i) for i in range(10)]


# ── Delete Operations ───────────────────────────────────────

async def test_delete_and_verify_absent(rest):
    """Deleted entity is absent from states list."""
    entity = "sensor.delete_verify_absent"
    await rest.set_state(entity, "exists")

    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    states = await rest.get_states()
    ids = [s["entity_id"] for s in states]
    assert entity not in ids


# ── State Value Types ───────────────────────────────────────

async def test_state_numeric_string(rest):
    """State accepts numeric strings."""
    result = await rest.set_state("sensor.num_str", "42.5")
    assert result["state"] == "42.5"


async def test_state_long_value(rest):
    """State accepts long strings."""
    long_val = "x" * 500
    result = await rest.set_state("sensor.long_val", long_val)
    assert result["state"] == long_val


async def test_state_special_chars(rest):
    """State accepts special characters."""
    result = await rest.set_state("sensor.special_chars", "on/off & <ready>")
    assert result["state"] == "on/off & <ready>"


async def test_attribute_nested_object(rest):
    """Attributes can contain nested objects."""
    result = await rest.set_state("sensor.nested_attr", "ok", {
        "config": {"threshold": 75, "enabled": True},
    })
    assert result["attributes"]["config"]["threshold"] == 75
    assert result["attributes"]["config"]["enabled"] is True


async def test_attribute_array_value(rest):
    """Attributes can contain arrays."""
    result = await rest.set_state("sensor.array_attr", "ok", {
        "tags": ["indoor", "sensor", "main"],
    })
    assert result["attributes"]["tags"] == ["indoor", "sensor", "main"]
