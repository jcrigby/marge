"""
CTS -- Device Registry REST API Depth Tests

Tests GET/POST/DELETE /api/devices, entity-to-device assignment,
and device listing with entity counts.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


async def test_create_device(rest):
    """POST /api/devices creates a device."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"dev_{tag}",
            "name": f"Test Device {tag}",
            "manufacturer": "Acme",
            "model": "Widget-1000",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


async def test_list_devices(rest):
    """GET /api/devices returns device list."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"dev_list_{tag}", "name": f"List Device {tag}"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    devices = resp.json()
    assert isinstance(devices, list)
    ids = [d["device_id"] for d in devices]
    assert f"dev_list_{tag}" in ids


async def test_device_has_fields(rest):
    """Device entries have expected fields."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"dev_fields_{tag}",
            "name": "Fields Device",
            "manufacturer": "TestCo",
            "model": "Model-X",
            "area_id": "",
        },
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    devices = resp.json()
    found = [d for d in devices if d["device_id"] == f"dev_fields_{tag}"]
    assert len(found) == 1
    dev = found[0]
    assert dev["name"] == "Fields Device"
    assert dev["manufacturer"] == "TestCo"
    assert dev["model"] == "Model-X"
    assert "entity_count" in dev
    assert "entities" in dev


async def test_delete_device(rest):
    """DELETE /api/devices/{id} removes a device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_del_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": did, "name": "Delete Me"},
        headers=rest._headers(),
    )

    resp = await rest.client.delete(
        f"{rest.base_url}/api/devices/{did}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    resp2 = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    ids = [d["device_id"] for d in resp2.json()]
    assert did not in ids


async def test_assign_entity_to_device(rest):
    """POST /api/devices/{did}/entities/{eid} assigns entity."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_assign_{tag}"
    eid = f"sensor.dev_ent_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": did, "name": "Assign Device"},
        headers=rest._headers(),
    )
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/{did}/entities/{eid}",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Device should now show entity
    resp2 = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    devices = resp2.json()
    found = [d for d in devices if d["device_id"] == did]
    assert len(found) == 1
    assert eid in found[0]["entities"]
    assert found[0]["entity_count"] >= 1


async def test_device_upsert_updates_fields(rest):
    """POST /api/devices with same ID updates fields."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_upsert_{tag}"

    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": did, "name": "Original"},
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": did, "name": "Updated", "manufacturer": "NewCo"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    found = [d for d in resp.json() if d["device_id"] == did]
    assert found[0]["name"] == "Updated"
    assert found[0]["manufacturer"] == "NewCo"


async def test_device_missing_name_400(rest):
    """POST /api/devices without name returns 400."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"dev_noname_{tag}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_device_missing_id_400(rest):
    """POST /api/devices without device_id returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"name": "No ID Device"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_device_with_area(rest):
    """Device can be created with area_id."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_area_{tag}"

    # Create area first
    await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": f"area_{tag}", "name": f"Room {tag}"},
        headers=rest._headers(),
    )

    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": did, "name": "Area Device", "area_id": f"area_{tag}"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    found = [d for d in resp.json() if d["device_id"] == did]
    assert found[0]["area_id"] == f"area_{tag}"
