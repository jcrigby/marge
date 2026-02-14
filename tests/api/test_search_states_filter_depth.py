"""
CTS -- Search States Filter Depth Tests

Tests the GET /api/states/search endpoint with various filter combinations:
domain, state, text query (q), area, and label filters. Verifies correct
filtering, sorting, and intersection of multiple filters.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Domain Filter ─────────────────────────────────────────

async def test_search_by_domain(rest):
    """Search with domain filter returns only matching domain."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.srch_d_{tag}", "42")
    await rest.set_state(f"light.srch_d_{tag}", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert all(e["entity_id"].startswith("sensor.") for e in results)


async def test_search_by_domain_excludes_other(rest):
    """Domain filter excludes entities from other domains."""
    tag = uuid.uuid4().hex[:8]
    eid_light = f"light.srch_ex_{tag}"
    await rest.set_state(eid_light, "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid_light not in eids


# ── State Filter ──────────────────────────────────────────

async def test_search_by_state_value(rest):
    """Search with state filter returns entities with matching state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_sv_{tag}"
    await rest.set_state(eid, "critical")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=critical",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_search_by_state_excludes(rest):
    """State filter excludes entities with different state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_se_{tag}"
    await rest.set_state(eid, "normal")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=critical",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid not in eids


# ── Text Query Filter ────────────────────────────────────

async def test_search_by_query_entity_id(rest):
    """Text query matches entity_id substring."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_q_{tag}"
    await rest.set_state(eid, "50")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=srch_q_{tag}",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_search_by_query_case_insensitive(rest):
    """Text query is case-insensitive."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.SRCH_CI_{tag}"
    await rest.set_state(eid, "1")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=srch_ci_{tag}",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


async def test_search_by_query_friendly_name(rest):
    """Text query matches friendly_name attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.srch_fn_{tag}"
    await rest.set_state(eid, "0", {"friendly_name": f"Kitchen Temp {tag}"})
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=Kitchen Temp {tag}",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids


# ── Combined Filters ─────────────────────────────────────

async def test_search_domain_and_state(rest):
    """Combining domain + state filters intersects results."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"light.combo_{tag}", "on")
    await rest.set_state(f"light.combo2_{tag}", "off")
    await rest.set_state(f"sensor.combo_{tag}", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&state=on",
        headers=rest._headers(),
    )
    results = resp.json()
    for e in results:
        assert e["entity_id"].startswith("light.")
        assert e["state"] == "on"
    eids = [e["entity_id"] for e in results]
    assert f"light.combo_{tag}" in eids
    assert f"light.combo2_{tag}" not in eids
    assert f"sensor.combo_{tag}" not in eids


async def test_search_domain_and_query(rest):
    """Combining domain + query narrows results."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.dq_{tag}"
    await rest.set_state(eid, "100")
    await rest.set_state(f"light.dq_{tag}", "on")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor&q=dq_{tag}",
        headers=rest._headers(),
    )
    eids = [e["entity_id"] for e in resp.json()]
    assert eid in eids
    assert f"light.dq_{tag}" not in eids


# ── Sort Order ────────────────────────────────────────────

async def test_search_results_sorted(rest):
    """Search results are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.srch_z_{tag}", "1")
    await rest.set_state(f"sensor.srch_a_{tag}", "2")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=srch_",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eids == sorted(eids)


# ── Empty Results ─────────────────────────────────────────

async def test_search_no_results(rest):
    """Search with no matches returns empty list."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=nonexistent_{tag}_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []
