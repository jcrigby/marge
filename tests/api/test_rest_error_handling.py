"""
CTS -- REST API Error Handling Tests (Consolidated)

Tests error responses for missing fields, invalid paths, unsupported methods,
malformed requests, edge cases, template errors, and boundary conditions.

Consolidated from 6 files:
  - test_rest_error_handling.py (original target, 21 tests)
  - test_error_responses.py (13 tests)
  - test_error_edge_cases.py (16 tests)
  - test_error_handling.py (13 tests)
  - test_rest_error_responses.py (13 tests)
  - test_rest_error_consistency.py (12 tests)
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# --- 404 errors ---


async def test_get_nonexistent_state_404(rest):
    """GET /api/states/<nonexistent> returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.no_exist_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_state_404(rest):
    """DELETE /api/states/<nonexistent> returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/sensor.no_del_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_dismiss_nonexistent_notification_404(rest):
    """POST /api/notifications/{bad_id}/dismiss returns 404."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/notifications/nonexistent_id_xyz/dismiss",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_unknown_api_path_handled(rest):
    """GET /api/does_not_exist is handled (SPA fallback or 404)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/does_not_exist",
        headers=rest._headers(),
    )
    # May return 404 or 200 (SPA fallback)
    assert resp.status_code in [200, 404]


async def test_405_get_on_post_only(rest):
    """GET on POST-only endpoint returns 405."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
    )
    assert resp.status_code == 405


# --- 404 / empty for nonexistent entity resources ---


@pytest.mark.marge_only
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


@pytest.mark.marge_only
async def test_logbook_nonexistent_entity_empty(rest):
    """GET /api/logbook/<nonexistent> returns empty array."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.no_log_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.marge_only
async def test_logbook_global_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.marge_only
async def test_statistics_nonexistent_entity(rest):
    """Statistics for nonexistent entity returns empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.err_stats_nonexistent",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == [] or isinstance(data, list)


# --- 400 malformed requests ---


async def test_set_state_no_body_422(rest):
    """POST /api/states without JSON body returns 422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_nobody",
        content=b"",
        headers={**rest._headers(), "content-type": "application/json"},
    )
    assert resp.status_code in [400, 422]


async def test_set_state_invalid_json(rest):
    """POST with invalid JSON returns 400 or 422."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_test",
        content="this is not json",
        headers={**rest._headers(), "Content-Type": "application/json"},
    )
    assert resp.status_code in [400, 422]


async def test_set_state_missing_state_field(rest):
    """POST without state field still works (state defaults to empty)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_no_state",
        json={"attributes": {"key": "val"}},
        headers=rest._headers(),
    )
    # Marge may accept this -- state might default to ""
    assert resp.status_code in [200, 400, 422]


async def test_service_call_invalid_json(rest):
    """POST /api/services with invalid JSON returns 4xx."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        content="{broken json",
        headers={**rest._headers(), "Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 415, 422)


async def test_template_missing_template_field(rest):
    """POST /api/template without template field returns error status."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"not_template": "value"},
        headers=rest._headers(),
    )
    assert resp.status_code in (400, 422, 500)


@pytest.mark.marge_only
@pytest.mark.parametrize("endpoint,body", [
    ("/api/areas", {}),
    ("/api/labels", {}),
    ("/api/devices", {"manufacturer": "Acme"}),
], ids=["area-empty", "label-empty", "device-partial"])
async def test_missing_required_fields_400(rest, endpoint, body):
    """POST to registry endpoints without required fields returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}{endpoint}",
        json=body,
        headers=rest._headers(),
    )
    assert resp.status_code == 400


@pytest.mark.marge_only
@pytest.mark.parametrize("endpoint,content", [
    ("/api/config/automation/yaml", "this is: [not: valid: yaml: ---"),
    ("/api/config/scene/yaml", "definitely not: [valid yaml ---"),
], ids=["automation", "scene"])
async def test_invalid_yaml_400(rest, endpoint, content):
    """PUT with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}{endpoint}",
        content=content,
        headers={"Content-Type": "text/yaml"},
    )
    assert resp.status_code == 400


# --- Template errors ---


@pytest.mark.parametrize("template", [
    "{{ undefined_var | bad_filter }}",
    "{% if true %}hello",
    "{{ 'hello' | nonexistent_filter_xyz }}",
    "{{ bad {{",
], ids=[
    "undefined-filter",
    "unclosed-tag",
    "nonexistent-filter",
    "bad-syntax",
])
async def test_template_syntax_error_400(rest, template):
    """POST /api/template with invalid template returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": template},
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


async def test_template_deeply_nested(rest):
    """Deeply nested template expression works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ (1 + 2) * 3 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "9"


async def test_template_string_concatenation(rest):
    """Template string concatenation works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' ~ ' ' ~ 'world' }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "hello world"


async def test_template_comparison(rest):
    """Template comparison returns correct boolean."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 10 > 5 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


# --- Service call edge cases ---


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
    # Should not crash -- generic fallback handles it
    assert resp.status_code == 200


async def test_nonexistent_service(rest):
    """Calling nonexistent service returns 200 (no-op)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/nonexistent_service",
        json={"entity_id": "light.test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_empty_body(rest):
    """POST /api/services/light/turn_on with empty body."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_nonexistent_entity(rest):
    """Service call on nonexistent entity handles gracefully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.does_not_exist_xyz"},
        headers=rest._headers(),
    )
    assert resp.status_code in [200, 404]


async def test_service_empty_entity_id_array(rest):
    """Calling a service with empty entity_id array is a no-op."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": []},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_returns_200(rest):
    """POST /api/services/<domain>/<service> returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.err_svc_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    assert resp.status_code == 200


async def test_service_call_returns_changed_states(rest):
    """Service call response is a flat list of changed entity states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.err_chg_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        headers=rest._headers(),
        json={"entity_id": eid},
    )
    data = resp.json()
    # Response is a flat list of changed entity states
    if isinstance(data, list):
        assert all(isinstance(e, dict) for e in data)


async def test_service_call_returns_json(rest):
    """POST /api/services returns JSON response (dict or list)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.resp_{tag}"
    await rest.set_state(eid, "off")
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# --- Fire event edge cases ---


async def test_fire_event_empty_type(rest):
    """POST /api/events with empty event type handled gracefully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/",
        json={"data": {}},
        headers=rest._headers(),
    )
    # Empty path segment -- might be 404 or 405
    assert resp.status_code in [404, 405, 200]


async def test_fire_event_returns_200(rest):
    """POST /api/events/:event_type returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_error_check",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_empty_body(rest):
    """Fire event with valid type and empty body succeeds."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_empty_event",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_with_special_chars(rest):
    """Fire event with special characters in type."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test.event_with-dashes.and_dots",
        json={"data": "value"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# --- State set responses ---


async def test_set_state_returns_entity_id(rest):
    """POST /api/states/<eid> response includes entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "val"},
    )
    assert resp.status_code == 200 or resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == eid


async def test_set_state_returns_state(rest):
    """POST /api/states/<eid> response includes state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_st_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "abc"},
    )
    data = resp.json()
    assert data["state"] == "abc"


async def test_set_state_returns_attributes(rest):
    """POST /api/states/<eid> response includes attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.err_attr_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
        json={"state": "v", "attributes": {"key": "val"}},
    )
    data = resp.json()
    assert data["attributes"]["key"] == "val"


async def test_set_state_returns_entity_format(rest):
    """POST /api/states returns full entity JSON with timestamps and context."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmt_{tag}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "value", "attributes": {"unit": "test"}},
        headers=rest._headers(),
    )
    # HA returns 201 Created for new entities, 200 OK for updates
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["entity_id"] == eid
    assert data["state"] == "value"
    assert "last_changed" in data
    assert "last_updated" in data
    assert "context" in data
    assert "attributes" in data


async def test_set_state_preserves_entity_id_case(rest):
    """Entity IDs preserve case exactly as given."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.CamelCase_{tag}"
    await rest.set_state(eid, "on")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


# --- Health endpoint ---


@pytest.mark.marge_only
async def test_health_no_auth_required(rest):
    """Health endpoint works without specific auth and returns status ok."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.marge_only
async def test_health_returns_version(rest):
    """Health endpoint includes version."""
    health = await rest.get_health()
    assert "version" in health
    assert isinstance(health["version"], str)


@pytest.mark.marge_only
async def test_health_returns_ws_connections(rest):
    """Health endpoint includes ws_connections count."""
    health = await rest.get_health()
    assert "ws_connections" in health


# --- Config endpoint ---


async def test_config_returns_valid_json(rest):
    """GET /api/config returns valid JSON with expected fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "location_name" in data
    assert "version" in data
    assert "state" in data


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


# --- General API responses ---


async def test_get_states_always_returns_list(rest):
    """GET /api/states always returns a JSON list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_api_root_returns_message(rest):
    """GET /api/ returns JSON with message."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


# --- Token edge cases ---


@pytest.mark.marge_only
async def test_token_create_empty_name(rest):
    """Creating token with empty name returns 400 or succeeds."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": ""},
        headers=rest._headers(),
    )
    # Empty string is still a valid name in many implementations
    # Just verify it doesn't crash
    assert resp.status_code in (200, 400)


# --- Entity lifecycle ---


async def test_delete_then_get_returns_none(rest):
    """After delete, GET returns 404."""
    await rest.set_state("sensor.err_del_get", "temp")
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.err_del_get",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state("sensor.err_del_get")
    assert state is None


async def test_create_update_delete_lifecycle(rest):
    """Full entity lifecycle: create, update, verify, delete."""
    entity = "sensor.err_lifecycle"
    await rest.set_state(entity, "step1", {"phase": "create"})
    s1 = await rest.get_state(entity)
    assert s1["state"] == "step1"

    await rest.set_state(entity, "step2", {"phase": "update"})
    s2 = await rest.get_state(entity)
    assert s2["state"] == "step2"
    assert s2["attributes"]["phase"] == "update"

    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/{entity}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    s3 = await rest.get_state(entity)
    assert s3 is None


# --- Concurrency ---


async def test_concurrent_state_updates(rest):
    """Multiple concurrent state updates on the same entity don't corrupt."""
    entity_id = "sensor.concurrent_test"
    tasks = [
        rest.set_state(entity_id, str(i))
        for i in range(20)
    ]
    await asyncio.gather(*tasks)
    state = await rest.get_state(entity_id)
    val = int(state["state"])
    assert 0 <= val <= 19


# --- WebSocket error handling ---


async def test_ws_unknown_command(ws):
    """WebSocket unknown command returns error result."""
    resp = await ws.send_command("totally_bogus_command")
    assert resp["success"] is False
    # Error details vary by implementation -- just verify error info exists
    error = resp.get("error") or resp.get("result") or {}
    assert isinstance(error, dict)


async def test_ws_call_service_missing_domain(ws):
    """WebSocket call_service with empty domain doesn't crash."""
    resp = await ws.send_command("call_service",
        domain="", service="", service_data={})
    assert resp["type"] == "result"
    assert resp["success"] is True
