"""
CTS -- Search Area and Label Filter Depth Tests

Tests GET /api/states/search with area and label filter parameters,
individually and combined with domain, state, and q filters.
Exercises multi-filter intersections and empty-result edge cases.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_area(rest, area_id, name):
    """Helper: create an area via REST."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return area_id


async def _assign_area(rest, area_id, entity_id):
    """Helper: assign entity to area."""
    await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity_id}",
        headers=rest._headers(),
    )


async def _create_label(rest, label_id, name):
    """Helper: create a label via REST."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": label_id, "name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return label_id


async def _assign_label(rest, label_id, entity_id):
    """Helper: assign label to entity."""
    await rest.client.post(
        f"{rest.base_url}/api/labels/{label_id}/entities/{entity_id}",
        headers=rest._headers(),
    )


async def _cleanup_area(rest, area_id):
    await rest.client.delete(
        f"{rest.base_url}/api/areas/{area_id}",
        headers=rest._headers(),
    )


async def _cleanup_label(rest, label_id):
    await rest.client.delete(
        f"{rest.base_url}/api/labels/{label_id}",
        headers=rest._headers(),
    )


# ── Search by Area ─────────────────────────────────────────

async def test_search_by_area(rest):
    """Search with area filter returns entities in that area."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_sa_{tag}"
    eid1 = f"sensor.sa_in_{tag}"
    eid2 = f"sensor.sa_out_{tag}"

    await _create_area(rest, area_id, f"Room {tag}")
    await rest.set_state(eid1, "42")
    await rest.set_state(eid2, "99")
    await _assign_area(rest, area_id, eid1)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    found = {e["entity_id"] for e in resp.json()}
    assert eid1 in found
    assert eid2 not in found

    await _cleanup_area(rest, area_id)


async def test_search_by_area_empty(rest):
    """Search by non-existent area returns empty results."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area=no_such_area_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Search by Label ────────────────────────────────────────

async def test_search_by_label(rest):
    """Search with label filter returns entities with that label."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"lbl_sl_{tag}"
    eid1 = f"light.sl_tagged_{tag}"
    eid2 = f"light.sl_untagged_{tag}"

    await _create_label(rest, label_id, f"Label {tag}")
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "off")
    await _assign_label(rest, label_id, eid1)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={label_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    found = {e["entity_id"] for e in resp.json()}
    assert eid1 in found
    assert eid2 not in found

    await _cleanup_label(rest, label_id)


async def test_search_by_label_empty(rest):
    """Search by non-existent label returns empty results."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label=no_such_label_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Area + Domain ──────────────────────────────────────────

async def test_search_area_and_domain(rest):
    """Search with area + domain returns intersection."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_ad_{tag}"
    eid_light = f"light.ad_l_{tag}"
    eid_sensor = f"sensor.ad_s_{tag}"

    await _create_area(rest, area_id, f"Room AD {tag}")
    await rest.set_state(eid_light, "on")
    await rest.set_state(eid_sensor, "42")
    await _assign_area(rest, area_id, eid_light)
    await _assign_area(rest, area_id, eid_sensor)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}&domain=light",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_light in found
    assert eid_sensor not in found
    assert all(e["entity_id"].startswith("light.") for e in results)

    await _cleanup_area(rest, area_id)


# ── Label + Domain ─────────────────────────────────────────

async def test_search_label_and_domain(rest):
    """Search with label + domain returns intersection."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"lbl_ld_{tag}"
    eid_switch = f"switch.ld_s_{tag}"
    eid_sensor = f"sensor.ld_n_{tag}"

    await _create_label(rest, label_id, f"Label LD {tag}")
    await rest.set_state(eid_switch, "on")
    await rest.set_state(eid_sensor, "50")
    await _assign_label(rest, label_id, eid_switch)
    await _assign_label(rest, label_id, eid_sensor)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={label_id}&domain=switch",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_switch in found
    assert eid_sensor not in found

    await _cleanup_label(rest, label_id)


# ── Area + State ───────────────────────────────────────────

async def test_search_area_and_state(rest):
    """Search with area + state returns intersection."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_as_{tag}"
    eid_on = f"light.as_on_{tag}"
    eid_off = f"light.as_off_{tag}"

    await _create_area(rest, area_id, f"Room AS {tag}")
    await rest.set_state(eid_on, "on")
    await rest.set_state(eid_off, "off")
    await _assign_area(rest, area_id, eid_on)
    await _assign_area(rest, area_id, eid_off)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}&state=on",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_on in found
    assert eid_off not in found

    await _cleanup_area(rest, area_id)


# ── Label + State ──────────────────────────────────────────

async def test_search_label_and_state(rest):
    """Search with label + state returns intersection."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"lbl_ls_{tag}"
    eid_on = f"switch.ls_on_{tag}"
    eid_off = f"switch.ls_off_{tag}"

    await _create_label(rest, label_id, f"Label LS {tag}")
    await rest.set_state(eid_on, "on")
    await rest.set_state(eid_off, "off")
    await _assign_label(rest, label_id, eid_on)
    await _assign_label(rest, label_id, eid_off)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?label={label_id}&state=on",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_on in found
    assert eid_off not in found

    await _cleanup_label(rest, label_id)


# ── Area + Label (Intersection) ────────────────────────────

async def test_search_area_and_label(rest):
    """Search with area + label returns entities matching both."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_al_{tag}"
    label_id = f"lbl_al_{tag}"
    eid_both = f"sensor.al_both_{tag}"
    eid_area_only = f"sensor.al_area_{tag}"
    eid_label_only = f"sensor.al_label_{tag}"

    await _create_area(rest, area_id, f"Room AL {tag}")
    await _create_label(rest, label_id, f"Label AL {tag}")

    await rest.set_state(eid_both, "1")
    await rest.set_state(eid_area_only, "2")
    await rest.set_state(eid_label_only, "3")

    await _assign_area(rest, area_id, eid_both)
    await _assign_area(rest, area_id, eid_area_only)
    await _assign_label(rest, label_id, eid_both)
    await _assign_label(rest, label_id, eid_label_only)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}&label={label_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    found = {e["entity_id"] for e in resp.json()}
    assert eid_both in found
    assert eid_area_only not in found
    assert eid_label_only not in found

    await _cleanup_area(rest, area_id)
    await _cleanup_label(rest, label_id)


# ── Three-Way: Domain + Area + Label ──────────────────────

async def test_search_domain_area_label(rest):
    """Search with domain + area + label returns 3-way intersection."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_dal_{tag}"
    label_id = f"lbl_dal_{tag}"
    eid_match = f"light.dal_match_{tag}"
    eid_wrong_domain = f"sensor.dal_wd_{tag}"

    await _create_area(rest, area_id, f"Room DAL {tag}")
    await _create_label(rest, label_id, f"Label DAL {tag}")

    await rest.set_state(eid_match, "on")
    await rest.set_state(eid_wrong_domain, "42")

    await _assign_area(rest, area_id, eid_match)
    await _assign_area(rest, area_id, eid_wrong_domain)
    await _assign_label(rest, label_id, eid_match)
    await _assign_label(rest, label_id, eid_wrong_domain)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&area={area_id}&label={label_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_match in found
    assert eid_wrong_domain not in found

    await _cleanup_area(rest, area_id)
    await _cleanup_label(rest, label_id)


# ── Q + Area ──────────────────────────────────────────────

async def test_search_q_and_area(rest):
    """Search with q + area narrows by both text match and area."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_qa_{tag}"
    eid1 = f"sensor.qa_alpha_{tag}"
    eid2 = f"sensor.qa_beta_{tag}"

    await _create_area(rest, area_id, f"Room QA {tag}")
    await rest.set_state(eid1, "10")
    await rest.set_state(eid2, "20")
    await _assign_area(rest, area_id, eid1)
    await _assign_area(rest, area_id, eid2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}&q=alpha",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    found = {e["entity_id"] for e in resp.json()}
    assert eid1 in found
    assert eid2 not in found

    await _cleanup_area(rest, area_id)


# ── Four-Way: Domain + State + Area + Label ───────────────

async def test_search_four_way_filter(rest):
    """Search with domain + state + area + label returns 4-way intersection."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_4w_{tag}"
    label_id = f"lbl_4w_{tag}"
    eid_match = f"light.fw_on_{tag}"
    eid_wrong_state = f"light.fw_off_{tag}"

    await _create_area(rest, area_id, f"Room 4W {tag}")
    await _create_label(rest, label_id, f"Label 4W {tag}")

    await rest.set_state(eid_match, "on")
    await rest.set_state(eid_wrong_state, "off")

    await _assign_area(rest, area_id, eid_match)
    await _assign_area(rest, area_id, eid_wrong_state)
    await _assign_label(rest, label_id, eid_match)
    await _assign_label(rest, label_id, eid_wrong_state)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=light&state=on&area={area_id}&label={label_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    results = resp.json()
    found = {e["entity_id"] for e in results}
    assert eid_match in found
    assert eid_wrong_state not in found

    await _cleanup_area(rest, area_id)
    await _cleanup_label(rest, label_id)


# ── Sorted Results With Filters ───────────────────────────

async def test_search_area_results_sorted(rest):
    """Search results with area filter are sorted by entity_id."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"area_sort_{tag}"

    await _create_area(rest, area_id, f"Sort Room {tag}")
    eids = [f"sensor.z_sort_{tag}", f"sensor.a_sort_{tag}", f"sensor.m_sort_{tag}"]
    for eid in eids:
        await rest.set_state(eid, "1")
        await _assign_area(rest, area_id, eid)

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?area={area_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    result_eids = [e["entity_id"] for e in resp.json()]
    assert result_eids == sorted(result_eids)

    await _cleanup_area(rest, area_id)
