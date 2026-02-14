"""
CTS -- Search API Depth Tests

Tests GET /api/states/search with query params: q (text search),
domain, state, label, area filters, and combinations.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Text Query (q param) ────────────────────────────────

async def test_search_by_entity_id(rest):
    """Search by entity_id substring."""
    await rest.set_state("sensor.search_depth_abc", "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "search_depth_abc"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["entity_id"] == "sensor.search_depth_abc" for s in results)


async def test_search_by_friendly_name(rest):
    """Search by friendly_name attribute."""
    await rest.set_state("sensor.search_depth_fn", "50", {"friendly_name": "DepthUniqueTestName"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "DepthUniqueTestName"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["entity_id"] == "sensor.search_depth_fn" for s in results)


async def test_search_by_state_value(rest):
    """Search q param matches state value."""
    await rest.set_state("sensor.search_depth_sv", "unicorn_state_xyz")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "unicorn_state_xyz"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["entity_id"] == "sensor.search_depth_sv" for s in results)


async def test_search_case_insensitive(rest):
    """Search is case insensitive."""
    await rest.set_state("sensor.search_depth_ci", "100", {"friendly_name": "CaseInsensitiveTest"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "caseinsensitivetest"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["entity_id"] == "sensor.search_depth_ci" for s in results)


# ── Domain Filter ────────────────────────────────────────

async def test_search_by_domain(rest):
    """Filter by domain returns only matching entities."""
    await rest.set_state("light.search_depth_dom", "on")
    await rest.set_state("sensor.search_depth_dom_other", "50")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    for s in results:
        assert s["entity_id"].startswith("light.")


# ── State Filter ─────────────────────────────────────────

async def test_search_by_state(rest):
    """Filter by state value."""
    await rest.set_state("sensor.search_depth_st1", "on")
    await rest.set_state("sensor.search_depth_st2", "off")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"state": "on", "q": "search_depth_st"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["entity_id"] == "sensor.search_depth_st1" for s in results)
    assert not any(s["entity_id"] == "sensor.search_depth_st2" for s in results)


# ── Combined Filters ────────────────────────────────────

async def test_search_domain_and_state(rest):
    """Filter by both domain and state."""
    await rest.set_state("light.search_depth_ds", "on")
    await rest.set_state("switch.search_depth_ds", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"domain": "light", "state": "on"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    for s in results:
        assert s["entity_id"].startswith("light.")
        assert s["state"] == "on"


async def test_search_empty_q_returns_all(rest):
    """Empty q param returns entities (not filtered by text)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0


async def test_search_no_match(rest):
    """Search for nonexistent text returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "xyzzy_absolutely_nonexistent_12345"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 0


async def test_search_results_sorted(rest):
    """Search results are sorted by entity_id."""
    await rest.set_state("sensor.search_depth_sort_b", "1")
    await rest.set_state("sensor.search_depth_sort_a", "2")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params={"q": "search_depth_sort"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    ids = [s["entity_id"] for s in results]
    assert ids == sorted(ids)
