"""
CTS -- Error Handling Edge Cases

Tests API error responses for malformed requests, missing fields,
invalid methods, and boundary conditions.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Malformed Bodies ─────────────────────────────────────

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
    # Marge may accept this — state might default to ""
    assert resp.status_code in [200, 400, 422]


# ── 404 Responses ────────────────────────────────────────

async def test_get_nonexistent_entity(rest):
    """GET nonexistent entity returns 404."""
    state = await rest.get_state("sensor.absolutely_does_not_exist_xyz_123")
    assert state is None


async def test_delete_nonexistent_entity(rest):
    """DELETE nonexistent entity returns 404."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.del_nonexist_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


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


# ── Service Call Edge Cases ──────────────────────────────

async def test_service_call_empty_body(rest):
    """Service call with empty body handles gracefully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code in [200, 400]


async def test_service_call_nonexistent_entity(rest):
    """Service call on nonexistent entity handles gracefully."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": "light.does_not_exist_xyz"},
        headers=rest._headers(),
    )
    assert resp.status_code in [200, 404]


# ── Fire Event Edge Cases ────────────────────────────────

async def test_fire_event_empty_type(rest):
    """Fire event with valid type and empty body."""
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


# ── Health Endpoint ──────────────────────────────────────

async def test_health_no_auth_required(rest):
    """Health endpoint works without specific auth."""
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_returns_version(rest):
    """Health endpoint includes version."""
    health = await rest.get_health()
    assert "version" in health
    assert isinstance(health["version"], str)


async def test_health_returns_ws_connections(rest):
    """Health endpoint includes ws_connections count."""
    health = await rest.get_health()
    assert "ws_connections" in health


# ── Template Edge Cases ──────────────────────────────────

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


# ── Multiple Operations ──────────────────────────────────

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
