"""
CTS -- REST Error Response Consistency Tests

Verifies that error responses (404, 400) are consistent across
endpoints and return proper HTTP status codes.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── 404 responses ──────────────────────────────────────────

async def test_get_nonexistent_entity_404(rest):
    """GET /api/states/:entity_id returns 404 for missing entity."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/sensor.absolutely_nonexistent_404",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_get_nonexistent_history_entity(rest):
    """GET /api/history/period/:entity_id for missing entity returns empty or 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/sensor.no_history_404",
        headers=rest._headers(),
    )
    # Should return 200 with empty list, or 404
    assert resp.status_code in (200, 404)


async def test_get_nonexistent_logbook_entity(rest):
    """GET /api/logbook/:entity_id for missing entity returns empty or 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/logbook/sensor.no_logbook_404",
        headers=rest._headers(),
    )
    assert resp.status_code in (200, 404)


async def test_get_nonexistent_statistics(rest):
    """GET /api/statistics/:entity_id for missing entity returns empty or 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.no_stats_404",
        headers=rest._headers(),
    )
    assert resp.status_code in (200, 404)


# ── 400 responses ──────────────────────────────────────────

async def test_template_invalid_syntax_400(rest):
    """POST /api/template with bad syntax returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ bad {{"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_automation_yaml_invalid_400(rest):
    """PUT /api/config/automation/yaml with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content="not: [[[valid yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_scene_yaml_invalid_400(rest):
    """PUT /api/config/scene/yaml with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content="not: [[[valid yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 400


# ── Successful status codes ────────────────────────────────

async def test_set_state_returns_200(rest):
    """POST /api/states/:entity_id returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/states/sensor.err_test_{tag}",
        json={"state": "val"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_service_call_returns_200(rest):
    """POST /api/services/:domain/:service returns 200."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.err_svc_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_fire_event_returns_200(rest):
    """POST /api/events/:event_type returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_error_check",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_health_returns_200(rest):
    """GET /api/health returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/health",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_config_returns_200(rest):
    """GET /api/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
