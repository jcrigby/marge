"""
CTS -- Automation Config and YAML Roundtrip Depth Tests

Tests GET /api/config/automation/config metadata, GET/PUT
automation YAML roundtrip, reload endpoint, and YAML validation
error handling.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Automation Config Listing ─────────────────────────────

async def test_automation_config_list(rest):
    """GET /api/config/automation/config returns automation list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 6  # 6 demo automations


async def test_automation_config_has_id_and_alias(rest):
    """Each automation has id and alias fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "id" in auto
        assert "alias" in auto


async def test_automation_config_has_counts(rest):
    """Each automation has trigger_count, condition_count, action_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "trigger_count" in auto
        assert "condition_count" in auto
        assert "action_count" in auto
        assert auto["trigger_count"] >= 1
        assert auto["action_count"] >= 1


async def test_automation_config_has_mode(rest):
    """Each automation has a mode field (single, queued, etc.)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "mode" in auto


async def test_automation_config_has_enabled(rest):
    """Each automation has enabled field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for auto in data:
        assert "enabled" in auto
        assert isinstance(auto["enabled"], bool)


async def test_automation_morning_wakeup_in_list(rest):
    """Morning wakeup automation appears in config list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    data = resp.json()
    aliases = [a["alias"] for a in data]
    assert any("morning" in alias.lower() or "wakeup" in alias.lower() for alias in aliases)


# ── Automation YAML GET/PUT ───────────────────────────────

async def test_automation_yaml_get(rest):
    """GET /api/config/automation/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "alias" in resp.text
    assert "trigger" in resp.text


async def test_automation_yaml_content_type(rest):
    """Automation YAML response has text/yaml content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "yaml" in content_type


async def test_automation_yaml_roundtrip(rest):
    """GET automation YAML then PUT it back succeeds."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    yaml_text = resp.text

    put_resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content=yaml_text,
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["result"] == "ok"


async def test_automation_yaml_put_invalid(rest):
    """PUT invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content="this is not: valid: yaml: [[[",
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp.status_code == 400


# ── Reload ────────────────────────────────────────────────

async def test_automation_reload(rest):
    """POST /api/config/core/reload reloads automations."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
    assert data["automations_reloaded"] >= 6


async def test_automation_reload_via_config_path(rest):
    """POST /api/config/automation/reload also works."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/automation/reload",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "ok"
