"""
CTS -- Search Query Combinations Depth Tests

Tests GET /api/states/search with various query parameter
combinations: q filter, domain filter, state filter, combined
filters, and empty results.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Setup Helper ─────────────────────────────────────────

async def _create_search_entities(rest, tag):
    """Create test entities for search tests."""
    await rest.set_state(f"sensor.sq_{tag}_temp", "72", {"friendly_name": "Living Room Temp"})
    await rest.set_state(f"sensor.sq_{tag}_humid", "45", {"friendly_name": "Living Room Humidity"})
    await rest.set_state(f"light.sq_{tag}_main", "on", {"friendly_name": "Living Room Light"})
    await rest.set_state(f"switch.sq_{tag}_fan", "off", {"friendly_name": "Bedroom Fan"})


# ── Query by Domain ──────────────────────────────────────

async def test_search_by_domain(rest):
    """Search with domain filter returns only that domain."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"domain": "sensor", "q": f"sq_{tag}"},
    )
    data = resp.json()
    for entry in data:
        assert entry["entity_id"].startswith("sensor.")


async def test_search_domain_excludes_others(rest):
    """Search with domain=light excludes sensor and switch."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"domain": "light", "q": f"sq_{tag}"},
    )
    data = resp.json()
    eids = [e["entity_id"] for e in data]
    assert f"light.sq_{tag}_main" in eids
    assert f"sensor.sq_{tag}_temp" not in eids


# ── Query by State ───────────────────────────────────────

async def test_search_by_state(rest):
    """Search with state filter returns matching states."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"state": "on", "q": f"sq_{tag}"},
    )
    data = resp.json()
    for entry in data:
        assert entry["state"] == "on"


async def test_search_by_state_off(rest):
    """Search with state=off returns off entities."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"state": "off", "q": f"sq_{tag}"},
    )
    data = resp.json()
    eids = [e["entity_id"] for e in data]
    assert f"switch.sq_{tag}_fan" in eids


# ── Query String (q) ────────────────────────────────────

async def test_search_by_q_entity_id(rest):
    """Search with q matching entity_id substring."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"q": f"sq_{tag}_temp"},
    )
    data = resp.json()
    eids = [e["entity_id"] for e in data]
    assert f"sensor.sq_{tag}_temp" in eids


async def test_search_q_no_match_empty(rest):
    """Search with q that matches nothing returns empty."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"q": f"nonexistent_{tag}_zzz"},
    )
    data = resp.json()
    assert data == []


# ── Combined Filters ────────────────────────────────────

async def test_search_domain_and_state(rest):
    """Search with domain + state combined filter."""
    tag = uuid.uuid4().hex[:8]
    await _create_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"domain": "light", "state": "on", "q": f"sq_{tag}"},
    )
    data = resp.json()
    for entry in data:
        assert entry["entity_id"].startswith("light.")
        assert entry["state"] == "on"


async def test_search_returns_200(rest):
    """Search endpoint returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"q": "test"},
    )
    assert resp.status_code == 200


async def test_search_returns_array(rest):
    """Search endpoint returns array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
        params={"q": "test"},
    )
    assert isinstance(resp.json(), list)
