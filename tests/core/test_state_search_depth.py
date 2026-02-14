"""
CTS -- State Search API Depth Tests

Tests GET /api/states/search with various filter combinations,
sorting, case behavior, and combined domain+state+q filters.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_search_by_domain_only(rest):
    """Search by domain returns correct entities."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"light.sd_{tag}", "on")
    await rest.set_state(f"sensor.sd_{tag}", "val")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light"},
        headers=rest._headers(),
    )
    data = resp.json()
    for e in data:
        assert e["entity_id"].startswith("light.")


async def test_search_by_state_value(rest):
    """Search by state value returns matching entities."""
    tag = uuid.uuid4().hex[:8]
    unique_state = f"unique_{tag}"
    await rest.set_state(f"sensor.ssv_{tag}", unique_state)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"state": unique_state},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1
    for e in data:
        assert e["state"] == unique_state


async def test_search_by_q_entity_id(rest):
    """Search by q matches entity_id substring."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.searchq_{tag}"
    await rest.set_state(eid, "findme")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"searchq_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids


async def test_search_combined_domain_state(rest):
    """Combined domain + state filter."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"switch.combo_{tag}", "on")
    await rest.set_state(f"light.combo_{tag}", "on")
    await rest.set_state(f"switch.comboff_{tag}", "off")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "switch", "state": "on"},
        headers=rest._headers(),
    )
    data = resp.json()
    for e in data:
        assert e["entity_id"].startswith("switch.")
        assert e["state"] == "on"


async def test_search_combined_domain_q(rest):
    """Combined domain + q filter."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.dq_{tag}", "val")
    await rest.set_state(f"light.dq_{tag}", "on")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "sensor", "q": f"dq_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    for e in data:
        assert e["entity_id"].startswith("sensor.")
        assert f"dq_{tag}" in e["entity_id"]


async def test_search_no_results(rest):
    """Search with no matches returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "absolutely_impossible_match_xyz_999"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_search_results_sorted(rest):
    """Search results are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    # Create entities in reverse order
    for i in [3, 1, 2]:
        await rest.set_state(f"sensor.sort_{tag}_{i}", "val")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"sort_{tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert ids == sorted(ids)


async def test_search_no_filters_returns_all(rest):
    """Search with no filters returns all entities."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_search_q_matches_friendly_name(rest):
    """Search q matches friendly_name attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fnsd_{tag}"
    await rest.set_state(eid, "val", {"friendly_name": f"Unique Name {tag}"})

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": f"Unique Name {tag}"},
        headers=rest._headers(),
    )
    data = resp.json()
    ids = [e["entity_id"] for e in data]
    assert eid in ids
