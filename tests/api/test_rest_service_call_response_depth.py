"""
CTS -- REST Service Call Response Depth Tests

Tests POST /api/services/<domain>/<service> response format:
status codes, response body structure (changed_states key),
changed entity states, and error handling for unknown services.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Success Response ────────────────────────────────────

async def test_service_call_returns_200(rest):
    """Service call returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rscr_ok_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200


async def test_service_call_returns_json_with_changed_states(rest):
    """Service call returns JSON with changed_states key."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rscr_json_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    assert "changed_states" in data
    assert isinstance(data["changed_states"], list)


async def test_service_call_returns_changed_entities(rest):
    """Service call response includes changed entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rscr_chg_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()["changed_states"]
    changed_ids = [e["entity_id"] for e in data]
    assert eid in changed_ids


async def test_service_call_changed_entity_has_new_state(rest):
    """Changed entity in response has updated state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.rscr_new_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()["changed_states"]
    entity = next(e for e in data if e["entity_id"] == eid)
    assert entity["state"] == "on"


# ── Multi-entity Service Call ───────────────────────────

async def test_service_call_multiple_entities(rest):
    """Service call with multiple entities returns all."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.rscr_m{i}_{tag}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eids},
    )
    data = resp.json()["changed_states"]
    changed_ids = [e["entity_id"] for e in data]
    for eid in eids:
        assert eid in changed_ids


# ── No-op Service Call ──────────────────────────────────

async def test_service_call_noop_returns_empty_or_no_changes(rest):
    """No-op service call returns 200 with empty or no changed_states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"button.rscr_noop_{tag}"
    await rest.set_state(eid, "unknown")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/button/press",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200
    data = resp.json()
    # No-op may return {} or {"changed_states": []}
    if "changed_states" in data:
        assert len(data["changed_states"]) == 0


# ── Service with Attributes ────────────────────────────

async def test_service_call_with_attrs_in_response(rest):
    """Service call response includes updated attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.rscr_attr_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid, "brightness": 200},
    )
    data = resp.json()["changed_states"]
    entity = next(e for e in data if e["entity_id"] == eid)
    assert entity["attributes"]["brightness"] == 200


# ── Unknown Service ─────────────────────────────────────

async def test_service_call_unknown_service(rest):
    """Unknown service still returns 200 (empty changes)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/nonexistent_service",
        headers=rest._headers(),
        json={"entity_id": "switch.whatever"},
    )
    assert resp.status_code == 200
