"""
CTS -- Search & Filter API Depth Tests

Tests GET /api/states/search with various query combinations:
q (text), domain, state, label, area, and combined filters.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_search_by_text_query(rest):
    """Search by q parameter finds matching entities."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.searchable_{tag}"
    await rest.set_state(eid, "active")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"searchable_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_by_domain(rest):
    """Search by domain parameter filters by entity domain."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"light.search_dom_{tag}", "on")
    await rest.set_state(f"switch.search_dom_{tag}", "on")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light"},
        headers=rest._headers(),
    )
    data = resp.json()
    for entity in data:
        assert entity["entity_id"].startswith("light.")


async def test_search_by_state_value(rest):
    """Search by state parameter filters by state value."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.search_state_{tag}", "special_value")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"state": "special_value"},
        headers=rest._headers(),
    )
    data = resp.json()
    for entity in data:
        assert entity["state"] == "special_value"


async def test_search_combined_domain_state(rest):
    """Search with domain + state combined filter."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.search_combo_{tag}", "on")
    await rest.set_state(f"light.search_combo_{tag}", "on")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "sensor", "state": "on"},
        headers=rest._headers(),
    )
    data = resp.json()
    for entity in data:
        assert entity["entity_id"].startswith("sensor.")
        assert entity["state"] == "on"


async def test_search_case_insensitive(rest):
    """Search q parameter is case-insensitive."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.CaseSearch_{tag}"
    await rest.set_state(eid, "val")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"casesearch_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_sorted_results(rest):
    """Search results are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.z_sort_{tag}", "val")
    await rest.set_state(f"sensor.a_sort_{tag}", "val")
    await rest.set_state(f"sensor.m_sort_{tag}", "val")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"sort_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert ids == sorted(ids)


async def test_search_no_results(rest):
    """Search with no matches returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "absolutely_nothing_matches_this_xyz_999"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_by_friendly_name(rest):
    """Search matches against friendly_name attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fn_search_{tag}"
    await rest.set_state(eid, "val", {"friendly_name": f"Friendly Sensor {tag}"})

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"Friendly Sensor {tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_with_label_filter(rest):
    """Search by label parameter filters by assigned label."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lbl_search_{tag}"
    lid = f"lbl_search_{tag}"

    await rest.set_state(eid, "val")
    await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": lid, "name": f"Search Label {tag}"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/labels/{lid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"label": lid},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_with_area_filter(rest):
    """Search by area parameter filters by assigned area."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.area_search_{tag}"
    aid = f"area_search_{tag}"

    await rest.set_state(eid, "val")
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": aid, "name": f"Search Area {tag}"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"area": aid},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_empty_params(rest):
    """Search with no params returns all entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0


async def test_search_results_have_entity_fields(rest):
    """Search results have standard entity fields."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.search_fields_{tag}"
    await rest.set_state(eid, "val", {"unit": "test"})

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"search_fields_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    entity = data[0]
    assert "entity_id" in entity
    assert "state" in entity
    assert "attributes" in entity
