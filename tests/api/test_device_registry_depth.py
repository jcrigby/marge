"""
CTS -- Device Registry REST API Depth Tests

Tests device CRUD, entity assignment, manufacturer/model fields,
and area association via the REST device endpoints.
"""

import pytest

pytestmark = pytest.mark.asyncio

_PREFIX = "cts_devdepth"


async def test_device_create(rest):
    """POST /api/devices creates a device."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"{_PREFIX}_hub1",
            "name": "Smart Hub",
            "manufacturer": "Acme",
            "model": "Hub-3000",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_device_list(rest):
    """Created device appears in GET /api/devices."""
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"{_PREFIX}_list1",
            "name": "List Device",
            "manufacturer": "TestCo",
            "model": "M1",
        },
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [d["device_id"] for d in data]
    assert f"{_PREFIX}_list1" in ids


async def test_device_has_fields(rest):
    """Device entries include name, manufacturer, model, area_id."""
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": f"{_PREFIX}_fields",
            "name": "Field Device",
            "manufacturer": "FieldCo",
            "model": "F-100",
            "area_id": "living_room",
        },
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    data = resp.json()
    dev = next(d for d in data if d["device_id"] == f"{_PREFIX}_fields")
    assert dev["name"] == "Field Device"
    assert dev["manufacturer"] == "FieldCo"
    assert dev["model"] == "F-100"
    assert "entity_count" in dev


async def test_device_assign_entity(rest):
    """POST /api/devices/:id/entities/:eid assigns entity to device."""
    await rest.set_state("sensor.dev_assign_test", "42")
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_assign", "name": "Assign Dev"},
        headers=rest._headers(),
    )
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/{_PREFIX}_assign/entities/sensor.dev_assign_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_device_entity_appears_in_list(rest):
    """Assigned entity appears in device's entities array."""
    await rest.set_state("sensor.dev_elist", "1")
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_elist", "name": "EList Dev"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/devices/{_PREFIX}_elist/entities/sensor.dev_elist",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    data = resp.json()
    dev = next(d for d in data if d["device_id"] == f"{_PREFIX}_elist")
    assert "sensor.dev_elist" in dev["entities"]
    assert dev["entity_count"] >= 1


async def test_device_delete(rest):
    """DELETE /api/devices/:id removes device."""
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_del", "name": "Delete Dev"},
        headers=rest._headers(),
    )
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/devices/{_PREFIX}_del",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_device_create_missing_name(rest):
    """Creating device without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_noname"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_device_create_missing_id(rest):
    """Creating device without device_id returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"name": "No ID Device"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_device_upsert(rest):
    """Creating device with same ID updates it."""
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_upsert", "name": "V1", "model": "old"},
        headers=rest._headers(),
    )
    await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"device_id": f"{_PREFIX}_upsert", "name": "V2", "model": "new"},
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    data = resp.json()
    dev = next(d for d in data if d["device_id"] == f"{_PREFIX}_upsert")
    assert dev["name"] == "V2"
    assert dev["model"] == "new"
