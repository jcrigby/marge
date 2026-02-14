"""
CTS -- Set State Response Format Depth Tests

Tests that POST /api/states/{entity_id} returns the full EntityState
object with all required fields: entity_id, state, attributes,
last_changed, last_updated, last_reported, and context.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _set_state_raw(rest, eid, state, attrs=None):
    """Set state and return raw response JSON."""
    body = {"state": state}
    if attrs:
        body["attributes"] = attrs
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json=body,
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Response Contains Required Fields ────────────────────

async def test_response_has_entity_id(rest):
    """POST response includes entity_id matching request."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_eid_{tag}"
    data = await _set_state_raw(rest, eid, "42")
    assert data["entity_id"] == eid


async def test_response_has_state(rest):
    """POST response includes the state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_state_{tag}"
    data = await _set_state_raw(rest, eid, "hello")
    assert data["state"] == "hello"


async def test_response_has_attributes(rest):
    """POST response includes attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_attr_{tag}"
    data = await _set_state_raw(rest, eid, "42", {"unit": "W"})
    assert data["attributes"]["unit"] == "W"


async def test_response_has_last_changed(rest):
    """POST response includes last_changed timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_lc_{tag}"
    data = await _set_state_raw(rest, eid, "1")
    assert "last_changed" in data
    assert "T" in data["last_changed"]


async def test_response_has_last_updated(rest):
    """POST response includes last_updated timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_lu_{tag}"
    data = await _set_state_raw(rest, eid, "2")
    assert "last_updated" in data
    assert "T" in data["last_updated"]


async def test_response_has_last_reported(rest):
    """POST response includes last_reported timestamp."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_lr_{tag}"
    data = await _set_state_raw(rest, eid, "3")
    assert "last_reported" in data


async def test_response_has_context(rest):
    """POST response includes context with id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_ctx_{tag}"
    data = await _set_state_raw(rest, eid, "4")
    assert "context" in data
    assert "id" in data["context"]
    assert len(data["context"]["id"]) > 0


# ── Response Reflects Updates ────────────────────────────

async def test_response_reflects_state_update(rest):
    """Second POST returns updated state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_upd_{tag}"
    await _set_state_raw(rest, eid, "A")
    data = await _set_state_raw(rest, eid, "B")
    assert data["state"] == "B"


async def test_response_context_changes(rest):
    """Each POST returns a different context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_ctxchg_{tag}"
    d1 = await _set_state_raw(rest, eid, "X")
    d2 = await _set_state_raw(rest, eid, "Y")
    assert d1["context"]["id"] != d2["context"]["id"]


async def test_response_attrs_empty_default(rest):
    """POST without attributes returns empty attributes dict."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_empty_{tag}"
    data = await _set_state_raw(rest, eid, "1")
    assert isinstance(data["attributes"], dict)


async def test_response_matches_get(rest):
    """POST response matches subsequent GET /api/states/{eid}."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_match_{tag}"
    post_data = await _set_state_raw(rest, eid, "42", {"unit": "W"})
    get_state = await rest.get_state(eid)
    assert post_data["state"] == get_state["state"]
    assert post_data["entity_id"] == get_state["entity_id"]
    assert post_data["attributes"]["unit"] == get_state["attributes"]["unit"]
    assert post_data["context"]["id"] == get_state["context"]["id"]


# ── Nested and Complex Attributes ────────────────────────

async def test_response_nested_attribute(rest):
    """POST with nested object in attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_nested_{tag}"
    data = await _set_state_raw(rest, eid, "1", {
        "config": {"threshold": 50, "enabled": True},
    })
    assert data["attributes"]["config"]["threshold"] == 50
    assert data["attributes"]["config"]["enabled"] is True


async def test_response_array_attribute(rest):
    """POST with array in attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_arr_{tag}"
    data = await _set_state_raw(rest, eid, "1", {
        "options": ["a", "b", "c"],
    })
    assert data["attributes"]["options"] == ["a", "b", "c"]


async def test_response_numeric_state_is_string(rest):
    """State is always returned as string, even for numeric input."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ssr_numstr_{tag}"
    data = await _set_state_raw(rest, eid, "42")
    assert isinstance(data["state"], str)
    assert data["state"] == "42"
