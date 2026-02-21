"""
CTS -- Miscellaneous API Endpoint Tests

Tests endpoints: /api/ status, /api/services listing, /api/events listing,
/api/webhook, /api/backup, /api/statistics, /api/sim/time,
/metrics (Prometheus), automation YAML get/put.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── API Status ───────────────────────────────────────────

async def test_api_root_status(rest):
    """GET /api/ returns API running message."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "running" in data["message"].lower()


# ── Service Listing ──────────────────────────────────────

async def test_list_services_returns_list(rest):
    """GET /api/services returns list of domain/services."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_list_services_has_domain(rest):
    """Each service entry has domain field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    for entry in data:
        assert "domain" in entry
        assert "services" in entry


async def test_list_services_has_light(rest):
    """Light domain appears in service listing."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    domains = [e["domain"] for e in data]
    assert "light" in domains


async def test_list_services_light_has_turn_on(rest):
    """Light domain has turn_on service."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    data = resp.json()
    light = next(e for e in data if e["domain"] == "light")
    assert "turn_on" in light["services"]


# ── Event Listing ────────────────────────────────────────

async def test_list_events_returns_list(rest):
    """GET /api/events returns event type list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/events",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── Webhook ──────────────────────────────────────────────

@pytest.mark.marge_only
async def test_webhook_accepts_post(rest):
    """POST /api/webhook/{id} returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/test_hook_depth",
        json={"payload": "test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Backup ───────────────────────────────────────────────

@pytest.mark.marge_only
async def test_backup_returns_data(rest):
    """GET /api/backup returns backup data."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Statistics ───────────────────────────────────────────

@pytest.mark.marge_only
async def test_statistics_endpoint(rest):
    """GET /api/statistics/{entity_id} returns data."""
    await rest.set_state("sensor.stat_depth_test", "42")
    resp = await rest.client.get(
        f"{rest.base_url}/api/statistics/sensor.stat_depth_test",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Sim Time ─────────────────────────────────────────────

@pytest.mark.marge_only
async def test_sim_time_set_and_verify(rest):
    """POST /api/sim/time updates sim time visible in health."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        json={"time": "14:30:00", "chapter": "afternoon", "speed": 5},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    health = await rest.get_health()
    assert health["sim_time"] == "14:30:00"
    assert health["sim_chapter"] == "afternoon"
    assert health["sim_speed"] == 5


# ── Prometheus Metrics ───────────────────────────────────

@pytest.mark.marge_only
async def test_metrics_endpoint(rest):
    """GET /metrics returns Prometheus format."""
    resp = await rest.client.get(f"{rest.base_url}/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "marge_" in text or "entity" in text.lower() or "state" in text.lower()


# ── Automation YAML ──────────────────────────────────────

@pytest.mark.marge_only
async def test_get_automation_yaml(rest):
    """GET /api/config/automation/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.text) > 0


@pytest.mark.marge_only
async def test_automation_reload_via_alt_path(rest):
    """POST /api/config/automation/reload also works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "automations_reloaded" in data
