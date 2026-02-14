"""
CTS -- Search Area + Label Pipeline Depth Tests

Tests the full pipeline from creating areas/labels, assigning entities,
and verifying search filters correctly include/exclude entities.
Covers area search, label search, combined filters, and unassignment.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_area(rest, area_id, name):
    """Create an area."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": name},
        headers=rest._headers(),
    )
    assert resp.status_code in (200, 201)


async def _assign_area(rest, area_id, entity_id):
    """Assign entity to area."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def _unassign_area(rest, area_id, entity_id):
    """Unassign entity from area."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/areas/{area_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    return resp


async def _create_label(rest, label_id, name, color=""):
    """Create a label."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"label_id": label_id, "name": name, "color": color},
        headers=rest._headers(),
    )
    assert resp.status_code in (200, 201)


async def _assign_label(rest, label_id, entity_id):
    """Assign label to entity."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels/{label_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def _unassign_label(rest, label_id, entity_id):
    """Unassign label from entity."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/labels/{label_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    return resp


async def _search(rest, **params):
    """Search entities with given filters."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search",
        params=params,
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Area Search Pipeline ──────────────────────────────────

async def test_search_by_area_finds_assigned(rest):
    """Entities assigned to area appear in area search."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_room_{tag}"
    eid = f"light.sal_in_{tag}"

    await rest.set_state(eid, "on")
    await _create_area(rest, area_id, f"Room {tag}")
    await _assign_area(rest, area_id, eid)

    results = await _search(rest, area=area_id)
    eids = [r["entity_id"] for r in results]
    assert eid in eids


async def test_search_by_area_excludes_unassigned(rest):
    """Entities not in the area don't appear in area search."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_exc_{tag}"
    eid_in = f"light.sal_ain_{tag}"
    eid_out = f"light.sal_aout_{tag}"

    await rest.set_state(eid_in, "on")
    await rest.set_state(eid_out, "on")
    await _create_area(rest, area_id, f"Excl Room {tag}")
    await _assign_area(rest, area_id, eid_in)

    results = await _search(rest, area=area_id)
    eids = [r["entity_id"] for r in results]
    assert eid_in in eids
    assert eid_out not in eids


async def test_search_area_after_unassign(rest):
    """Unassigned entity no longer appears in area search."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_una_{tag}"
    eid = f"sensor.sal_una_{tag}"

    await rest.set_state(eid, "42")
    await _create_area(rest, area_id, f"Unassign Room {tag}")
    await _assign_area(rest, area_id, eid)

    # Verify it's there
    results = await _search(rest, area=area_id)
    assert eid in [r["entity_id"] for r in results]

    # Unassign
    await _unassign_area(rest, area_id, eid)

    # Verify gone
    results = await _search(rest, area=area_id)
    assert eid not in [r["entity_id"] for r in results]


# ── Label Search Pipeline ─────────────────────────────────

async def test_search_by_label_finds_assigned(rest):
    """Entities with label appear in label search."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"sal_lbl_{tag}"
    eid = f"switch.sal_lin_{tag}"

    await rest.set_state(eid, "off")
    await _create_label(rest, label_id, f"Label {tag}")
    await _assign_label(rest, label_id, eid)

    results = await _search(rest, label=label_id)
    eids = [r["entity_id"] for r in results]
    assert eid in eids


async def test_search_by_label_excludes_unlabeled(rest):
    """Entities without the label don't appear in label search."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"sal_lexc_{tag}"
    eid_labeled = f"sensor.sal_lb_{tag}"
    eid_unlabeled = f"sensor.sal_nolb_{tag}"

    await rest.set_state(eid_labeled, "1")
    await rest.set_state(eid_unlabeled, "2")
    await _create_label(rest, label_id, f"Excl Label {tag}")
    await _assign_label(rest, label_id, eid_labeled)

    results = await _search(rest, label=label_id)
    eids = [r["entity_id"] for r in results]
    assert eid_labeled in eids
    assert eid_unlabeled not in eids


async def test_search_label_after_unassign(rest):
    """Unlabeled entity no longer appears in label search."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"sal_lunr_{tag}"
    eid = f"light.sal_lunr_{tag}"

    await rest.set_state(eid, "on")
    await _create_label(rest, label_id, f"UnLabel {tag}")
    await _assign_label(rest, label_id, eid)

    # Verify it's there
    results = await _search(rest, label=label_id)
    assert eid in [r["entity_id"] for r in results]

    # Unassign
    await _unassign_label(rest, label_id, eid)

    # Verify gone
    results = await _search(rest, label=label_id)
    assert eid not in [r["entity_id"] for r in results]


# ── Combined Filters ──────────────────────────────────────

async def test_search_area_plus_domain(rest):
    """Area + domain filter narrows results correctly."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_ad_{tag}"
    eid_light = f"light.sal_ad_{tag}"
    eid_sensor = f"sensor.sal_ad_{tag}"

    await rest.set_state(eid_light, "on")
    await rest.set_state(eid_sensor, "42")
    await _create_area(rest, area_id, f"AD Room {tag}")
    await _assign_area(rest, area_id, eid_light)
    await _assign_area(rest, area_id, eid_sensor)

    # Search for lights in area only
    results = await _search(rest, area=area_id, domain="light")
    eids = [r["entity_id"] for r in results]
    assert eid_light in eids
    assert eid_sensor not in eids


async def test_search_label_plus_state(rest):
    """Label + state filter narrows results correctly."""
    tag = uuid.uuid4().hex[:8]
    label_id = f"sal_ls_{tag}"
    eid_on = f"switch.sal_lson_{tag}"
    eid_off = f"switch.sal_lsoff_{tag}"

    await rest.set_state(eid_on, "on")
    await rest.set_state(eid_off, "off")
    await _create_label(rest, label_id, f"LS Label {tag}")
    await _assign_label(rest, label_id, eid_on)
    await _assign_label(rest, label_id, eid_off)

    # Search for labeled entities with state=on
    results = await _search(rest, label=label_id, state="on")
    eids = [r["entity_id"] for r in results]
    assert eid_on in eids
    assert eid_off not in eids


async def test_search_area_plus_q(rest):
    """Area + q filter narrows results."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_aq_{tag}"
    eid_match = f"sensor.sal_match_{tag}"
    eid_other = f"sensor.sal_other_{tag}"

    await rest.set_state(eid_match, "1")
    await rest.set_state(eid_other, "2")
    await _create_area(rest, area_id, f"AQ Room {tag}")
    await _assign_area(rest, area_id, eid_match)
    await _assign_area(rest, area_id, eid_other)

    results = await _search(rest, area=area_id, q="sal_match")
    eids = [r["entity_id"] for r in results]
    assert eid_match in eids
    assert eid_other not in eids


async def test_search_empty_area(rest):
    """Search on area with no entities returns empty."""
    tag = uuid.uuid4().hex[:8]
    area_id = f"sal_empty_{tag}"
    await _create_area(rest, area_id, f"Empty {tag}")

    results = await _search(rest, area=area_id)
    assert results == []
