"""
CTS -- Search API Combination Depth Tests

Tests GET /api/states/search with combined filter parameters:
domain+state, q+domain, domain+state+q, and verifies sorting.
Also tests the DELETE /api/states/{entity_id} endpoint and
GET /api/states/{entity_id} 404 behavior.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Domain Filter ─────────────────────────────────────────

async def test_search_by_domain(rest):
    """GET /api/states/search?domain=X filters by domain."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_dom_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert all(e["entity_id"].startswith("sensor.") for e in results)
    assert any(e["entity_id"] == eid for e in results)


# ── State Filter ──────────────────────────────────────────

async def test_search_by_state(rest):
    """GET /api/states/search?state=X filters by state value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_st_{tag}"
    await rest.set_state(eid, "unique_state_42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=unique_state_42",
        headers=rest._headers(),
    )
    results = resp.json()
    assert any(e["entity_id"] == eid for e in results)
    assert all(e["state"] == "unique_state_42" for e in results)


# ── Text Query ────────────────────────────────────────────

async def test_search_by_q_entity_id(rest):
    """GET /api/states/search?q=X matches entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srch_q_{tag}"
    await rest.set_state(eid, "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q={tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    assert any(e["entity_id"] == eid for e in results)


async def test_search_by_q_friendly_name(rest):
    """GET /api/states/search?q=X matches friendly_name."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_fn_{tag}"
    await rest.set_state(eid, "50", {"friendly_name": f"UniqueSearch{tag}"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=UniqueSearch{tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    assert any(e["entity_id"] == eid for e in results)


# ── Combined Filters ─────────────────────────────────────

async def test_search_domain_and_state(rest):
    """Search with domain+state returns intersection."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.srch_ds_{tag}"
    await rest.set_state(eid, "on")
    await rest.set_state(f"switch.srch_ds_{tag}", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&state=on",
        headers=rest._headers(),
    )
    results = resp.json()
    assert all(e["entity_id"].startswith("light.") for e in results)
    assert all(e["state"] == "on" for e in results)
    assert any(e["entity_id"] == eid for e in results)


async def test_search_domain_and_q(rest):
    """Search with domain+q returns filtered results."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_dq_{tag}"
    await rest.set_state(eid, "99")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor&q={tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    assert all(e["entity_id"].startswith("sensor.") for e in results)
    assert any(e["entity_id"] == eid for e in results)


# ── Sorted Results ────────────────────────────────────────

async def test_search_results_sorted(rest):
    """Search results are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.z_sort_{tag}", "1")
    await rest.set_state(f"sensor.a_sort_{tag}", "2")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=sort_{tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eids == sorted(eids)


# ── DELETE entity ─────────────────────────────────────────

async def test_delete_entity(rest):
    """DELETE /api/states/{entity_id} removes entity."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.del_{tag}"
    await rest.set_state(eid, "42")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Confirm entity is gone
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_returns_404(rest):
    """DELETE on non-existent entity returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.nonexistent_xyz_99",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_get_nonexistent_entity_returns_404(rest):
    """GET /api/states/{entity_id} on non-existent entity returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.nonexistent_xyz_99",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── API Status and Config ────────────────────────────────

async def test_api_status(rest):
    """GET /api/ returns API running message."""
    resp = await rest.client.get(f"{rest.base_url}/api/")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


async def test_api_config(rest):
    """GET /api/config returns system config."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["location_name"] == "Marge Demo Home"
    assert data["time_zone"] == "America/Denver"
    assert data["state"] == "RUNNING"


async def test_api_config_has_coordinates(rest):
    """GET /api/config has latitude and longitude."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert abs(data["latitude"] - 40.3916) < 0.01
    assert abs(data["longitude"] - (-111.8508)) < 0.01


async def test_api_config_has_units(rest):
    """GET /api/config has unit_system."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    data = resp.json()
    units = data["unit_system"]
    assert units["length"] == "mi"
    assert units["mass"] == "lb"
    assert units["volume"] == "gal"
