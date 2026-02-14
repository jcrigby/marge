"""
CTS -- Automation Reload and YAML Validation Depth Tests

Tests automation reload via POST /api/config/core/reload and
/api/config/automation/reload, YAML roundtrip preservation,
and invalid YAML rejection.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


# ── Reload endpoints ──────────────────────────────────────

async def test_reload_core_returns_200(rest):
    """POST /api/config/core/reload returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_reload_core_returns_json(rest):
    """Reload response is JSON with result field."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "result" in data


async def test_reload_automation_path_returns_200(rest):
    """POST /api/config/automation/reload returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_reload_preserves_automations(rest):
    """Reload preserves automation count."""
    # Get automation count before
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    before_count = len(resp1.json())

    # Reload
    await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)

    # Count after
    resp2 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    after_count = len(resp2.json())

    assert before_count == after_count


async def test_reload_idempotent(rest):
    """Multiple reloads produce same result."""
    for _ in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/config/core/reload",
            headers=rest._headers(),
        )
        assert resp.status_code == 200
    await asyncio.sleep(0.2)

    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── YAML endpoints ─────────────────────────────────────────

async def test_get_automation_yaml_returns_200(rest):
    """GET /api/config/automation/yaml returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_get_automation_yaml_content_type(rest):
    """GET /api/config/automation/yaml returns text/yaml."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert "text/yaml" in resp.headers.get("content-type", "")


async def test_get_automation_yaml_has_content(rest):
    """Automation YAML is non-empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert len(resp.text.strip()) > 0


async def test_get_automation_yaml_has_trigger(rest):
    """Automation YAML references trigger keyword."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert "trigger" in resp.text


async def test_put_automation_yaml_invalid_returns_400(rest):
    """PUT with unparseable YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content="not_valid: [[[yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_put_automation_yaml_roundtrip(rest):
    """GET YAML then PUT it back succeeds and reports count."""
    get_resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    original = get_resp.text

    put_resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content=original,
        headers=rest._headers(),
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data.get("result") == "ok"
    assert "automations_reloaded" in data
    assert data["automations_reloaded"] >= 1


async def test_reload_after_yaml_roundtrip_stable(rest):
    """Automation entities survive YAML roundtrip."""
    # Read and write back
    get_resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content=get_resp.text,
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)

    # Verify entities still exist
    states = await rest.get_states()
    auto_entities = [s for s in states if s["entity_id"].startswith("automation.")]
    assert len(auto_entities) >= 1
