"""
CTS -- REST API Error Handling Tests

Tests error responses for missing fields, invalid paths,
unsupported methods, and edge cases in API endpoints.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_set_state_no_body_422(rest):
    """POST /api/states without JSON body returns 422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_nobody",
        content=b"",
        headers={**rest._headers(), "content-type": "application/json"},
    )
    assert resp.status_code in [400, 422]


async def test_call_service_unknown_domain(rest):
    """POST /api/services/unknown_domain/turn_on returns 200 (no-op)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"unknown_domain.err_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/unknown_domain/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    # Should not crash — generic fallback handles it
    assert resp.status_code == 200


async def test_fire_event_empty_type(rest):
    """POST /api/events with empty event type handled gracefully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/",
        json={"data": {}},
        headers=rest._headers(),
    )
    # Empty path segment — might be 404 or 405
    assert resp.status_code in [404, 405, 200]


async def test_get_history_nonexistent_entity(rest):
    """GET /api/history/period for nonexistent entity returns empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.no_such_entity_xyz_999",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


async def test_template_render_error(rest):
    """POST /api/template with invalid template returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ undefined_var | bad_filter }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_template_empty_string(rest):
    """POST /api/template with empty template returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text == ""


async def test_areas_missing_fields_400(rest):
    """POST /api/areas without required fields returns 400."""
    # Missing both
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400

    # Missing name
    resp2 = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={"area_id": "test_area"},
        headers=rest._headers(),
    )
    assert resp2.status_code == 400


async def test_dismiss_nonexistent_notification_404(rest):
    """POST /api/notifications/{bad_id}/dismiss returns 404."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/nonexistent_id_xyz/dismiss",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_get_states_always_returns_list(rest):
    """GET /api/states always returns a JSON list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_config_check_returns_result(rest):
    """POST /api/config/core/check_config always has result field."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert data["result"] in ["valid", "invalid"]


async def test_unknown_api_path_handled(rest):
    """GET /api/does_not_exist is handled (SPA fallback or 404)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/does_not_exist",
        headers=rest._headers(),
    )
    # May return 404 or 200 (SPA fallback)
    assert resp.status_code in [200, 404]


async def test_service_call_empty_body(rest):
    """POST /api/services/light/turn_on with empty body."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_set_state_preserves_entity_id_case(rest):
    """Entity IDs preserve case exactly as given."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.CamelCase_{tag}"
    await rest.set_state(eid, "on")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid
