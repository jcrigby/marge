"""
CTS -- Error Handling & Negative Tests

Tests error conditions, validation failures, missing resources,
malformed requests, and edge cases.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Missing / Not Found ──────────────────────────────────

async def test_get_nonexistent_entity(rest):
    """GET /api/states/<nonexistent> returns 404."""
    resp = await rest.client.get(f"{rest.base_url}/api/states/sensor.does_not_exist_xyz")
    assert resp.status_code == 404


async def test_delete_nonexistent_entity(rest):
    """DELETE /api/states/<nonexistent> returns 404."""
    resp = await rest.client.request(
        "DELETE", f"{rest.base_url}/api/states/sensor.never_existed_xyz"
    )
    assert resp.status_code == 404


async def test_dismiss_nonexistent_notification(rest):
    """POST /api/notifications/<nonexistent>/dismiss returns 404."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/notif_never_existed/dismiss"
    )
    assert resp.status_code == 404


# ── Malformed Requests ────────────────────────────────────

async def test_set_state_missing_body(rest):
    """POST /api/states/<entity> with empty body returns 422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.test_bad_body",
        content="",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 422)


async def test_set_state_invalid_json(rest):
    """POST /api/states/<entity> with invalid JSON returns 400/422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.test_bad_json",
        content="{not valid json",
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


async def test_create_token_missing_name(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
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


# ── Template Errors ───────────────────────────────────────

async def test_template_syntax_error(rest):
    """POST /api/template with invalid template returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ invalid | unknownfilter }}"},
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


async def test_concurrent_service_calls(rest):
    """Multiple concurrent service calls on different entities succeed."""
    import asyncio

    async def toggle_entity(idx):
        eid = f"switch.conc_test_{idx}"
        await rest.set_state(eid, "off")
        await rest.call_service("switch", "toggle", {"entity_id": eid})
        s = await rest.get_state(eid)
        return s["state"]

    results = await asyncio.gather(*[toggle_entity(i) for i in range(10)])
    assert all(s == "on" for s in results)


# ── History / Logbook edge cases ──────────────────────────

async def test_history_nonexistent_entity(rest):
    """GET /api/history/period/<nonexistent> returns empty list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.never_existed_history"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


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


async def test_ws_render_template_error(ws):
    """WebSocket render_template with bad template returns error."""
    resp = await ws.send_command("render_template",
        template="{{ unknown_function() }}")
    assert resp["success"] is False


# ── Automation reload path ────────────────────────────────

async def test_automation_reload_endpoint(rest):
    """POST /api/config/automation/reload returns success."""
    resp = await rest.client.post(f"{rest.base_url}/api/config/automation/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
