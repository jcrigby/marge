"""
CTS -- Device-Area Integration Depth Tests

Tests interactions between device registry and area registry: devices
with area_id, device update via upsert, multi-entity devices across
domains, entity state returned in area entity listings, and device
entity reassignment.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_device(rest, device_id, name, **kwargs):
    body = {"device_id": device_id, "name": name}
    body.update(kwargs)
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json=body,
    )
    assert resp.status_code == 200
    return resp.json()


async def _get_device(rest, device_id):
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    return next((d for d in resp.json() if d["device_id"] == device_id), None)


async def _create_area(rest, area_id, name):
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": area_id, "name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def _get_area(rest, area_id):
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
    )
    return next((a for a in resp.json() if a["area_id"] == area_id), None)


# ── Device with area_id ──────────────────────────────────

async def test_device_with_area_id(rest):
    """Device created with area_id retains it."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_area_{tag}"
    aid = f"area_dev_{tag}"
    await _create_area(rest, aid, f"Room {tag}")
    await _create_device(rest, did, f"Device {tag}", area_id=aid)
    device = await _get_device(rest, did)
    assert device is not None
    assert device["area_id"] == aid


async def test_device_area_id_empty_default(rest):
    """Device without area_id has empty string."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_noarea_{tag}"
    await _create_device(rest, did, f"No Area {tag}")
    device = await _get_device(rest, did)
    assert device["area_id"] == ""


# ── Device Upsert (update) ──────────────────────────────

async def test_device_upsert_updates_name(rest):
    """Creating device with same ID updates the name."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_upsert_{tag}"
    await _create_device(rest, did, "Original Name")
    await _create_device(rest, did, "Updated Name")
    device = await _get_device(rest, did)
    assert device["name"] == "Updated Name"


async def test_device_upsert_updates_manufacturer(rest):
    """Upserting device updates manufacturer."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_mfr_{tag}"
    await _create_device(rest, did, "Dev", manufacturer="OldCo")
    await _create_device(rest, did, "Dev", manufacturer="NewCo")
    device = await _get_device(rest, did)
    assert device["manufacturer"] == "NewCo"


async def test_device_upsert_updates_model(rest):
    """Upserting device updates model."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_model_{tag}"
    await _create_device(rest, did, "Dev", model="T-100")
    await _create_device(rest, did, "Dev", model="T-200")
    device = await _get_device(rest, did)
    assert device["model"] == "T-200"


# ── Multi-Entity Multi-Domain Device ─────────────────────

async def test_device_multi_domain_entities(rest):
    """Device can have entities from multiple domains."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_multi_{tag}"
    await _create_device(rest, did, f"Multi {tag}")

    eids = [
        f"light.multi_{tag}",
        f"sensor.multi_{tag}",
        f"switch.multi_{tag}",
    ]
    for eid in eids:
        await rest.set_state(eid, "on")
        await rest.client.post(
            f"{rest.base_url}/api/devices/{did}/entities/{eid}",
            headers=rest._headers(),
        )

    device = await _get_device(rest, did)
    assert device["entity_count"] == 3
    for eid in eids:
        assert eid in device["entities"]


async def test_device_entity_count_zero_initially(rest):
    """New device has entity_count 0."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_zero_{tag}"
    await _create_device(rest, did, f"Empty {tag}")
    device = await _get_device(rest, did)
    assert device["entity_count"] == 0
    assert device["entities"] == []


# ── Area Entity Listing Returns State Objects ────────────

async def test_area_entity_listing_has_state(rest):
    """Area entity listing returns full state objects with state field."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_state_{tag}"
    eid = f"sensor.astate_{tag}"
    await _create_area(rest, aid, f"State Room {tag}")
    await rest.set_state(eid, "42")
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    entities = resp.json()
    found = next((e for e in entities if e["entity_id"] == eid), None)
    assert found is not None
    assert found["state"] == "42"


async def test_area_entity_listing_has_attributes(rest):
    """Area entity listing includes attributes."""
    tag = uuid.uuid4().hex[:8]
    aid = f"area_attrs_{tag}"
    eid = f"light.aattr_{tag}"
    await _create_area(rest, aid, f"Attr Room {tag}")
    await rest.set_state(eid, "on", {"brightness": 200})
    await rest.client.post(
        f"{rest.base_url}/api/areas/{aid}/entities/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/areas/{aid}/entities",
        headers=rest._headers(),
    )
    entities = resp.json()
    found = next((e for e in entities if e["entity_id"] == eid), None)
    assert found is not None
    assert found["attributes"]["brightness"] == 200


# ── Delete Device Cleans Up ──────────────────────────────

async def test_delete_device_removes_from_list(rest):
    """Deleting device removes it from the listing."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_delrm_{tag}"
    await _create_device(rest, did, "To Delete")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/{did}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    device = await _get_device(rest, did)
    assert device is None


async def test_delete_nonexistent_device(rest):
    """Deleting a non-existent device returns 200 (idempotent)."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/nonexistent_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Device Missing Required Fields ───────────────────────

async def test_create_device_missing_name_fails(rest):
    """Device creation without name returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"device_id": f"dev_noname_{tag}"},
    )
    assert resp.status_code == 400


async def test_create_device_missing_device_id_fails(rest):
    """Device creation without device_id returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
        json={"name": f"No ID {tag}"},
    )
    assert resp.status_code == 400
