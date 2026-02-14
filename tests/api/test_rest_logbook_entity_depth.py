"""
CTS -- REST Logbook Entity-Specific Depth Tests

Tests GET /api/logbook/<entity_id> endpoint for entity-specific
logbook entries, filtering, and response format.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Entity Logbook ──────────────────────────────────────

async def test_logbook_entity_returns_200(rest):
    """GET /api/logbook/<eid> returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rled_log_{tag}"
    await rest.set_state(eid, "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_logbook_entity_returns_array(rest):
    """Entity logbook returns JSON array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rled_arr_{tag}"
    await rest.set_state(eid, "test")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entity_returns_list(rest):
    """Entity logbook always returns list."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rled_ent_{tag}"
    await rest.set_state(eid, "a")
    await rest.set_state(eid, "b")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_logbook_entry_has_entity_id(rest):
    """Logbook entries have entity_id field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rled_eid_{tag}"
    await rest.set_state(eid, "val")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        assert "entity_id" in data[0]


async def test_logbook_entity_filtered(rest):
    """Entity logbook only shows entries for that entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rled_filt_{tag}"
    other = f"sensor.rled_other_{tag}"
    await rest.set_state(eid, "x")
    await rest.set_state(other, "y")
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert entry.get("entity_id") == eid


async def test_logbook_global_returns_200(rest):
    """GET /api/logbook returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
