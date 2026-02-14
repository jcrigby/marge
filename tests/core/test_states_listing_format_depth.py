"""
CTS -- GET /api/states Listing Format Depth Tests

Tests the full states listing endpoint: EntityState format in array,
multi-domain entities, attributes present, timestamps present,
context present, and domain-based filtering via search.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Listing Format ───────────────────────────────────────

async def test_states_returns_list(rest):
    """GET /api/states returns a list."""
    states = await rest.get_states()
    assert isinstance(states, list)


async def test_states_entry_has_entity_id(rest):
    """Each entry in states list has entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_eid_{tag}"
    await rest.set_state(eid, "42")
    states = await rest.get_states()
    found = next((s for s in states if s["entity_id"] == eid), None)
    assert found is not None


async def test_states_entry_has_state(rest):
    """Each entry in states list has state field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_state_{tag}"
    await rest.set_state(eid, "hello")
    states = await rest.get_states()
    found = next(s for s in states if s["entity_id"] == eid)
    assert found["state"] == "hello"


async def test_states_entry_has_attributes(rest):
    """Each entry in states list has attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_attr_{tag}"
    await rest.set_state(eid, "1", {"unit": "W"})
    states = await rest.get_states()
    found = next(s for s in states if s["entity_id"] == eid)
    assert found["attributes"]["unit"] == "W"


async def test_states_entry_has_timestamps(rest):
    """Each entry has last_changed, last_updated, last_reported."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_ts_{tag}"
    await rest.set_state(eid, "1")
    states = await rest.get_states()
    found = next(s for s in states if s["entity_id"] == eid)
    assert "last_changed" in found
    assert "last_updated" in found
    assert "last_reported" in found


async def test_states_entry_has_context(rest):
    """Each entry has context with id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_ctx_{tag}"
    await rest.set_state(eid, "1")
    states = await rest.get_states()
    found = next(s for s in states if s["entity_id"] == eid)
    assert "context" in found
    assert "id" in found["context"]


# ── Multi-Domain Listing ─────────────────────────────────

async def test_multi_domain_all_present(rest):
    """Entities from different domains all appear in listing."""
    tag = uuid.uuid4().hex[:8]
    eids = [
        f"light.lst_md_{tag}",
        f"switch.lst_md_{tag}",
        f"sensor.lst_md_{tag}",
        f"cover.lst_md_{tag}",
    ]
    for eid in eids:
        await rest.set_state(eid, "on")
    states = await rest.get_states()
    listed_eids = {s["entity_id"] for s in states}
    for eid in eids:
        assert eid in listed_eids


async def test_created_then_deleted_not_in_list(rest):
    """Deleted entity doesn't appear in states listing."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_del_{tag}"
    await rest.set_state(eid, "1")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    states = await rest.get_states()
    listed_eids = {s["entity_id"] for s in states}
    assert eid not in listed_eids


# ── Domain Search ────────────────────────────────────────

async def test_search_domain_only_returns_matching(rest):
    """Search with domain filter returns only matching entities."""
    tag = uuid.uuid4().hex[:8]
    eid_light = f"light.lst_dom_{tag}"
    eid_sensor = f"sensor.lst_dom_{tag}"
    await rest.set_state(eid_light, "on")
    await rest.set_state(eid_sensor, "42")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&q={tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid_light in eids
    assert eid_sensor not in eids


async def test_search_q_matches_entity_id(rest):
    """Search with q= matches entity_id substring."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lst_q_{tag}"
    await rest.set_state(eid, "99")
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q={tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid in eids


async def test_search_state_filter(rest):
    """Search with state filter returns matching state entities."""
    tag = uuid.uuid4().hex[:8]
    eid_on = f"light.lst_sf_on_{tag}"
    eid_off = f"light.lst_sf_off_{tag}"
    await rest.set_state(eid_on, "on")
    await rest.set_state(eid_off, "off")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?state=on&q={tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    eids = [e["entity_id"] for e in results]
    assert eid_on in eids
    assert eid_off not in eids


async def test_search_results_sorted(rest):
    """Search results are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    eids = [
        f"sensor.lst_sort_c_{tag}",
        f"sensor.lst_sort_a_{tag}",
        f"sensor.lst_sort_b_{tag}",
    ]
    for eid in eids:
        await rest.set_state(eid, "1")

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?q=lst_sort_{tag}",
        headers=rest._headers(),
    )
    results = resp.json()
    result_eids = [e["entity_id"] for e in results]
    assert result_eids == sorted(result_eids)
