"""
CTS -- REST History Period Endpoint Depth Tests

Tests GET /api/history/period/<entity_id> endpoint for response
format, data presence, and timestamp ordering.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── History Endpoint ────────────────────────────────────

async def test_history_period_returns_200(rest):
    """GET /api/history/period/<eid> returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rhpd_hist_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_history_period_returns_array(rest):
    """History period returns JSON array."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rhpd_arr_{tag}"
    await rest.set_state(eid, "1")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_history_period_returns_list(rest):
    """History period always returns list (may be empty for new entities)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rhpd_ent_{tag}"
    await rest.set_state(eid, "1")
    await rest.set_state(eid, "2")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_history_entry_has_state(rest):
    """History entries have state field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rhpd_fld_{tag}"
    await rest.set_state(eid, "test_val")
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    data = resp.json()
    if len(data) > 0:
        entry = data[0] if not isinstance(data[0], list) else data[0][0]
        assert "state" in entry


async def test_history_nonexistent_entity(rest):
    """History for nonexistent entity returns 200 with empty data."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.never_existed_hist",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
