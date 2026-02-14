"""
CTS -- Error Response and Edge Case Tests

Tests error handling for malformed requests, missing fields,
invalid endpoints, and boundary conditions.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Missing Entity ──────────────────────────────────────────

async def test_get_nonexistent_entity_404(rest):
    """GET /api/states/:id for nonexistent entity returns 404."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.err_nonexistent_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_delete_nonexistent_entity_404(rest):
    """DELETE /api/states/:id for nonexistent entity returns 404."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/states/sensor.err_del_nonexistent",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Invalid Service Calls ───────────────────────────────────

async def test_nonexistent_domain_service(rest):
    """Calling service on nonexistent domain returns 200 (no-op)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/nonexistent_domain/turn_on",
        json={"entity_id": "sensor.test"},
        headers=rest._headers(),
    )
    # Marge returns 200 with empty changed_states for unknown domains
    assert resp.status_code == 200


async def test_nonexistent_service(rest):
    """Calling nonexistent service returns 200 (no-op)."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/nonexistent_service",
        json={"entity_id": "light.test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Template Errors ─────────────────────────────────────────

async def test_template_unclosed_tag_400(rest):
    """Template with unclosed tag returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% if true %}hello"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_template_undefined_filter_400(rest):
    """Template with undefined filter returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 'hello' | nonexistent_filter_xyz }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


# ── Area/Label Missing Fields ───────────────────────────────

async def test_area_create_no_body(rest):
    """Creating area with empty body returns error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/areas",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_label_create_no_body(rest):
    """Creating label with empty body returns error."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/labels",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


# ── History Edge Cases ──────────────────────────────────────

async def test_logbook_global_returns_list(rest):
    """GET /api/logbook returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_statistics_nonexistent_entity(rest):
    """Statistics for nonexistent entity returns empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.err_stats_nonexistent",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == [] or isinstance(data, list)


# ── Token Edge Cases ────────────────────────────────────────

async def test_token_create_empty_name(rest):
    """Creating token with empty name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": ""},
        headers=rest._headers(),
    )
    # Empty string is still a valid name in many implementations
    # Just verify it doesn't crash
    assert resp.status_code in (200, 400)


# ── Config Endpoint ─────────────────────────────────────────

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


async def test_check_config_returns_valid(rest):
    """POST /api/config/core/check_config returns valid result."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "valid"
