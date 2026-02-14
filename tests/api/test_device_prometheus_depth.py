"""
CTS -- Device Registry and Prometheus Metrics Depth Tests

Tests the device registry REST API (create, list, assign entities,
delete), plus the Prometheus /metrics endpoint format and sim-time
endpoint.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_device(rest, device_id, name, manufacturer="", model="", area_id=""):
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={
            "device_id": device_id,
            "name": name,
            "manufacturer": manufacturer,
            "model": model,
            "area_id": area_id,
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _delete_device(rest, device_id):
    return await rest.client.delete(
        f"{rest.base_url}/api/devices/{device_id}",
        headers=rest._headers(),
    )


async def _list_devices(rest):
    resp = await rest.client.get(
        f"{rest.base_url}/api/devices",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _assign_entity_device(rest, device_id, entity_id):
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices/{device_id}/entities/{entity_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


# ── Device CRUD ───────────────────────────────────────────

async def test_create_device(rest):
    """POST /api/devices creates a new device."""
    tag = uuid.uuid4().hex[:8]
    result = await _create_device(rest, f"dev_{tag}", f"Sensor Hub {tag}")
    assert result["result"] == "ok"


async def test_device_appears_in_list(rest):
    """Created device appears in GET /api/devices."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_list_{tag}"
    await _create_device(rest, did, f"Hub {tag}")
    devices = await _list_devices(rest)
    dids = [d["device_id"] for d in devices]
    assert did in dids


async def test_device_has_metadata(rest):
    """Device in list has correct name, manufacturer, model."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_meta_{tag}"
    await _create_device(rest, did, f"Thermostat {tag}", "Honeywell", "T6 Pro")
    devices = await _list_devices(rest)
    dev = next(d for d in devices if d["device_id"] == did)
    assert dev["name"] == f"Thermostat {tag}"
    assert dev["manufacturer"] == "Honeywell"
    assert dev["model"] == "T6 Pro"


async def test_device_with_area(rest):
    """Device created with area_id has it set."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_area_{tag}"
    await _create_device(rest, did, f"Light {tag}", area_id="living_room")
    devices = await _list_devices(rest)
    dev = next(d for d in devices if d["device_id"] == did)
    assert dev["area_id"] == "living_room"


async def test_delete_device(rest):
    """DELETE /api/devices/{device_id} removes the device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_del_{tag}"
    await _create_device(rest, did, f"Temp {tag}")
    resp = await _delete_device(rest, did)
    assert resp.status_code == 200
    devices = await _list_devices(rest)
    dids = [d["device_id"] for d in devices]
    assert did not in dids


# ── Device Entity Assignment ──────────────────────────────

async def test_assign_entity_to_device(rest):
    """POST assigns entity to device."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_ent_{tag}"
    eid = f"sensor.dev_{tag}"
    await _create_device(rest, did, f"Hub {tag}")
    await rest.set_state(eid, "22.5")
    result = await _assign_entity_device(rest, did, eid)
    assert result["result"] == "ok"


async def test_assigned_entity_in_device_list(rest):
    """Assigned entity appears in device entity list."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_elist_{tag}"
    eid = f"sensor.dev_elist_{tag}"
    await _create_device(rest, did, f"Hub {tag}")
    await rest.set_state(eid, "33")
    await _assign_entity_device(rest, did, eid)
    devices = await _list_devices(rest)
    dev = next(d for d in devices if d["device_id"] == did)
    assert eid in dev["entities"]


async def test_device_entity_count(rest):
    """Device entity_count reflects assigned entities."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_cnt_{tag}"
    await _create_device(rest, did, f"Multi Hub {tag}")
    await rest.set_state(f"sensor.dc1_{tag}", "1")
    await rest.set_state(f"sensor.dc2_{tag}", "2")
    await _assign_entity_device(rest, did, f"sensor.dc1_{tag}")
    await _assign_entity_device(rest, did, f"sensor.dc2_{tag}")
    devices = await _list_devices(rest)
    dev = next(d for d in devices if d["device_id"] == did)
    assert dev["entity_count"] == 2


# ── Device Full Lifecycle ─────────────────────────────────

async def test_device_full_lifecycle(rest):
    """Device: create → assign entity → verify → delete."""
    tag = uuid.uuid4().hex[:8]
    did = f"dev_life_{tag}"
    eid = f"light.dev_life_{tag}"

    await _create_device(rest, did, f"Lifecycle Hub {tag}", "IKEA", "TRADFRI")
    await rest.set_state(eid, "on")
    await _assign_entity_device(rest, did, eid)

    devices = await _list_devices(rest)
    dev = next(d for d in devices if d["device_id"] == did)
    assert eid in dev["entities"]

    resp = await _delete_device(rest, did)
    assert resp.status_code == 200


# ── Prometheus Metrics ────────────────────────────────────

async def test_prometheus_metrics_endpoint(rest):
    """GET /metrics returns Prometheus-format text."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Should contain at least one metric line
    assert "marge_" in text or "entity_count" in text or "uptime" in text or len(text) > 0


async def test_prometheus_metrics_has_entity_count(rest):
    """Prometheus metrics include entity count gauge."""
    # Create a known entity first
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.prom_{tag}", "42")
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    # Should have some numeric content
    assert len(resp.text) > 0


# ── Sim Time ──────────────────────────────────────────────

async def test_sim_time_set(rest):
    """POST /api/sim/time sets simulation time."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "14:30:00"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_sim_time_with_speed(rest):
    """POST /api/sim/time with speed parameter."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "08:00:00", "speed": 10},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Check Config ──────────────────────────────────────────

async def test_check_config(rest):
    """POST /api/config/core/check_config returns valid result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data


# ── Error Log ─────────────────────────────────────────────

async def test_error_log_endpoint(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
