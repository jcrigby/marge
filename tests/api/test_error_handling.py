"""
CTS -- Error Handling & Negative Tests

Tests error conditions, validation failures, missing resources,
malformed requests, and edge cases.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Malformed Requests ────────────────────────────────────

async def test_set_state_missing_body(rest):
    """POST /api/states/<entity> with empty body returns 422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.test_bad_body",
        content="",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 422)


async def test_create_area_missing_fields(rest):
    """POST /api/areas without required fields returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"name": "Test Room"},
    )
    assert resp.status_code == 400


async def test_create_device_missing_fields(rest):
    """POST /api/devices without required fields returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/devices",
        json={"manufacturer": "Acme"},
    )
    assert resp.status_code == 400


async def test_create_label_missing_fields(rest):
    """POST /api/labels without required fields returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={"color": "#ff0000"},
    )
    assert resp.status_code == 400


async def test_put_automation_yaml_invalid(rest):
    """PUT /api/config/automation/yaml with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content="this is: [not: valid: yaml: ---",
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 400


async def test_put_scene_yaml_invalid(rest):
    """PUT /api/config/scene/yaml with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content="definitely not: [valid yaml ---",
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 400


# ── Service Edge Cases ────────────────────────────────────

async def test_service_no_entity_id(rest):
    """Calling a service without entity_id doesn't crash."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={},
    )
    assert resp.status_code == 200


async def test_service_nonexistent_domain(rest):
    """Calling a service with bogus domain returns 200 (no-op)."""
    entity_id = "fake_domain.test_entity"
    await rest.set_state(entity_id, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fake_domain/fake_service",
        json={"entity_id": entity_id},
    )
    assert resp.status_code == 200


async def test_service_empty_entity_id_array(rest):
    """Calling a service with empty entity_id array is a no-op."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": []},
    )
    assert resp.status_code == 200


# ── Concurrency ───────────────────────────────────────────

async def test_concurrent_state_updates(rest):
    """Multiple concurrent state updates on the same entity don't corrupt."""
    import asyncio

    entity_id = "sensor.concurrent_test"
    tasks = [
        rest.set_state(entity_id, str(i))
        for i in range(20)
    ]
    await asyncio.gather(*tasks)
    state = await rest.get_state(entity_id)
    val = int(state["state"])
    assert 0 <= val <= 19


# ── History / Logbook edge cases ──────────────────────────

async def test_logbook_empty(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(f"{rest.base_url}/api/logbook")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── WebSocket Error Handling ──────────────────────────────

async def test_ws_unknown_command(ws):
    """WebSocket unknown command returns error result."""
    resp = await ws.send_command("totally_bogus_command")
    assert resp["success"] is False
    assert "Unknown" in resp.get("result", {}).get("message", "")


async def test_ws_call_service_missing_domain(ws):
    """WebSocket call_service with empty domain doesn't crash."""
    resp = await ws.send_command("call_service",
        domain="", service="", service_data={})
    assert resp["type"] == "result"
    assert resp["success"] is True
