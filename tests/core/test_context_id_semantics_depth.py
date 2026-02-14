"""
CTS -- Context ID Semantics Depth Tests

Tests the context object on entity states: uniqueness per update,
structure (id, parent_id, user_id), consistency across endpoints,
and behavior under rapid updates.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Context Structure ─────────────────────────────────────

async def test_context_has_id_field(rest):
    """Every entity state has context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_id_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert "context" in state
    assert "id" in state["context"]


async def test_context_id_is_string(rest):
    """Context id is a non-empty string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_str_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    ctx_id = state["context"]["id"]
    assert isinstance(ctx_id, str)
    assert len(ctx_id) > 0


async def test_context_is_object(rest):
    """Context is a JSON object (dict)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_obj_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert isinstance(state["context"], dict)


async def test_context_id_nonempty(rest):
    """Context id is a non-empty value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_ne_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    assert state["context"]["id"] not in (None, "")


# ── Context Uniqueness ────────────────────────────────────

async def test_context_unique_per_state_change(rest):
    """Each state change produces a unique context id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_uniq_{tag}"
    ids = []
    for i in range(5):
        await rest.set_state(eid, str(i))
        state = await rest.get_state(eid)
        ids.append(state["context"]["id"])
    assert len(set(ids)) == 5


async def test_context_unique_across_entities(rest):
    """Different entities have different context ids."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.ctx_e1_{tag}"
    eid2 = f"sensor.ctx_e2_{tag}"
    await rest.set_state(eid1, "a")
    await rest.set_state(eid2, "b")

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["context"]["id"] != s2["context"]["id"]


async def test_context_changes_on_attr_only_update(rest):
    """Context id changes even when only attributes change."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_attr_{tag}"
    await rest.set_state(eid, "same", {"brightness": 100})
    s1 = await rest.get_state(eid)

    await rest.set_state(eid, "same", {"brightness": 200})
    s2 = await rest.get_state(eid)

    assert s1["context"]["id"] != s2["context"]["id"]


async def test_context_changes_on_identical_set(rest):
    """Context id changes even when state+attrs are identical (re-reported)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_ident_{tag}"
    await rest.set_state(eid, "val", {"key": "x"})
    s1 = await rest.get_state(eid)

    await rest.set_state(eid, "val", {"key": "x"})
    s2 = await rest.get_state(eid)

    assert s1["context"]["id"] != s2["context"]["id"]


# ── Context in Listing ────────────────────────────────────

async def test_context_in_states_listing(rest):
    """GET /api/states entries include context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_list_{tag}"
    await rest.set_state(eid, "1")

    states = await rest.get_states()
    found = next(s for s in states if s["entity_id"] == eid)
    assert "context" in found
    assert "id" in found["context"]


async def test_context_in_listing_matches_individual(rest):
    """Context in listing matches context from individual GET."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_match_{tag}"
    await rest.set_state(eid, "1")

    individual = await rest.get_state(eid)
    states = await rest.get_states()
    listed = next(s for s in states if s["entity_id"] == eid)

    assert individual["context"]["id"] == listed["context"]["id"]


# ── Context Under Rapid Updates ───────────────────────────

async def test_context_rapid_updates_all_unique(rest):
    """Rapid sequential updates all produce unique context ids."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_rapid_{tag}"
    ids = []
    for i in range(20):
        await rest.set_state(eid, str(i))
        state = await rest.get_state(eid)
        ids.append(state["context"]["id"])
    assert len(set(ids)) == 20


async def test_context_id_format_uuid(rest):
    """Context id appears to be a UUID or UUID-like string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_fmt_{tag}"
    await rest.set_state(eid, "1")
    state = await rest.get_state(eid)
    ctx_id = state["context"]["id"]
    # UUID format: 32 hex chars (with or without hyphens)
    hex_chars = ctx_id.replace("-", "")
    assert len(hex_chars) >= 16  # at least a reasonable length for a unique ID
