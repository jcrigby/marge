"""
CTS -- Search API Combined Filter Tests

Tests GET /api/states/search with multiple filters combined:
domain+state, domain+q, state+q, and all three together.
"""

import asyncio
import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def setup_search_entities(rest, tag):
    """Create a set of entities for search testing."""
    await rest.set_state(f"light.search_{tag}_a", "on", {"friendly_name": f"Kitchen Light {tag}"})
    await rest.set_state(f"light.search_{tag}_b", "off", {"friendly_name": f"Bedroom Light {tag}"})
    await rest.set_state(f"sensor.search_{tag}_c", "on", {"friendly_name": f"Motion Sensor {tag}"})
    await rest.set_state(f"switch.search_{tag}_d", "on", {"friendly_name": f"Power Switch {tag}"})
    await rest.set_state(f"sensor.search_{tag}_e", "23.5", {"friendly_name": f"Temp Sensor {tag}"})


async def test_search_domain_only(rest):
    """Search by domain returns matching entities."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert all(r["entity_id"].startswith("light.") for r in results)


async def test_search_state_only(rest):
    """Search by state value returns matching entities."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"state": "on"},
        headers=rest._headers(),
    )
    results = resp.json()
    assert all(r["state"] == "on" for r in results)


async def test_search_domain_and_state(rest):
    """domain + state combined narrows results."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light", "state": "on"},
        headers=rest._headers(),
    )
    results = resp.json()
    for r in results:
        assert r["entity_id"].startswith("light.")
        assert r["state"] == "on"


async def test_search_domain_and_q(rest):
    """domain + q combined narrows results."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light", "q": f"search_{tag}"},
        headers=rest._headers(),
    )
    results = resp.json()
    found_ids = [r["entity_id"] for r in results]
    assert all(eid.startswith("light.") for eid in found_ids)
    assert any(f"search_{tag}" in eid for eid in found_ids)


async def test_search_q_matches_friendly_name(rest):
    """q parameter searches friendly_name attribute."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"Kitchen Light {tag}"},
        headers=rest._headers(),
    )
    results = resp.json()
    assert any(r["entity_id"] == f"light.search_{tag}_a" for r in results)


async def test_search_q_case_insensitive(rest):
    """q parameter is case insensitive."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"kitchen light {tag}"},
        headers=rest._headers(),
    )
    results = resp.json()
    assert any(r["entity_id"] == f"light.search_{tag}_a" for r in results)


async def test_search_no_filters_returns_all(rest):
    """Search with no filters returns all entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
    )
    results = resp.json()
    assert len(results) >= 1


async def test_search_no_match_returns_empty(rest):
    """Search with impossible filter returns empty array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "absolutely_impossible_match_xyz_999"},
        headers=rest._headers(),
    )
    results = resp.json()
    assert results == []


async def test_search_results_sorted_by_entity_id(rest):
    """Search results are sorted by entity_id."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "sensor"},
        headers=rest._headers(),
    )
    results = resp.json()
    entity_ids = [r["entity_id"] for r in results]
    assert entity_ids == sorted(entity_ids)


async def test_search_state_and_q(rest):
    """state + q combined narrows results."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"state": "on", "q": f"search_{tag}"},
        headers=rest._headers(),
    )
    results = resp.json()
    for r in results:
        assert r["state"] == "on"
        assert f"search_{tag}" in r["entity_id"].lower() or f"search_{tag}" in str(r.get("attributes", {})).lower()


async def test_search_all_three_filters(rest):
    """domain + state + q all combined."""
    tag = uuid.uuid4().hex[:8]
    await setup_search_entities(rest, tag)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "sensor", "state": "on", "q": f"search_{tag}"},
        headers=rest._headers(),
    )
    results = resp.json()
    for r in results:
        assert r["entity_id"].startswith("sensor.")
        assert r["state"] == "on"


# -- from test_extended_api.py --

async def test_search_by_area(rest):
    """Search by area_id returns entities assigned to that area."""
    # Create area and assign entity
    area_resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        json={"area_id": "search_area", "name": "Search Area"},
    )
    await rest.set_state("sensor.in_search_area", "42")
    await rest.client.post(
        f"{rest.base_url}/api/areas/search_area/entities/sensor.in_search_area",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area=search_area",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    entity_ids = [r["entity_id"] for r in results]
    assert "sensor.in_search_area" in entity_ids
