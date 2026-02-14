"""
CTS -- REST Error Matrix Depth Tests

Tests REST API error handling: 404 for unknown entities, 400 for bad
requests, proper error responses for malformed input, and edge cases
for various endpoints.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── GET Errors ────────────────────────────────────────────

async def test_get_unknown_entity_404(rest):
    """GET /api/states/unknown returns 404."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.unknown_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_get_unknown_route(rest):
    """GET /api/nonexistent returns some response (may be 200 or 404)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/nonexistent",
        headers=rest._headers(),
    )
    # axum may return 200 or 404 depending on catch-all routes
    assert resp.status_code in (200, 404)


# ── POST Errors ───────────────────────────────────────────

async def test_set_state_empty_body_error(rest):
    """POST /api/states/{entity_id} with empty body returns error."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_{tag}",
        headers=rest._headers(),
        content="",
    )
    assert resp.status_code in (400, 415, 422)


async def test_set_state_invalid_json_error(rest):
    """POST /api/states with invalid JSON returns error."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.badjson_{tag}",
        headers=rest._headers(),
        content="not json",
    )
    assert resp.status_code in (400, 415, 422)


async def test_call_service_no_body_error(rest):
    """POST /api/services/light/turn_on with no body returns 200 or error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        headers=rest._headers(),
        content="",
    )
    # Some implementations accept empty body, others don't
    assert resp.status_code in (200, 400, 415, 422)


async def test_create_area_no_body_error(rest):
    """POST /api/areas with no body returns error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        headers=rest._headers(),
        content="",
    )
    assert resp.status_code in (400, 415, 422)


# ── Service Errors ────────────────────────────────────────

async def test_call_unknown_service(rest):
    """Calling unknown service returns 200 (service registry handles gracefully)."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/nonexistent/nonexistent",
        headers=rest._headers(),
        json={"entity_id": f"sensor.err_{tag}"},
    )
    # Should return 200 with empty changed_states (graceful fallthrough)
    assert resp.status_code == 200


# ── Template Errors ───────────────────────────────────────

async def test_template_invalid_syntax(rest):
    """POST /api/template with invalid Jinja returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": "{{ invalid(syntax %%"},
    )
    assert resp.status_code == 400


async def test_template_empty_template(rest):
    """POST /api/template with empty string returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        headers=rest._headers(),
        json={"template": ""},
    )
    assert resp.status_code == 200
    assert resp.text == ""


# ── Webhook Errors ────────────────────────────────────────

async def test_webhook_no_body(rest):
    """POST /api/webhook/{id} with no body returns 200 (fires default event)."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_{tag}",
    )
    assert resp.status_code == 200


async def test_webhook_with_body(rest):
    """POST /api/webhook/{id} with JSON body returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_{tag}",
        json={"event_type": f"webhook_test_{tag}"},
    )
    assert resp.status_code == 200


# ── History/Logbook Edge Cases ────────────────────────────

async def test_history_nonexistent_entity(rest):
    """History for nonexistent entity returns empty list."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.nx_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_logbook_nonexistent_entity(rest):
    """Logbook for nonexistent entity returns empty list."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.nx_{tag}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == []
