"""
CTS -- YAML Read/Write Round-trip Tests

Tests automation and scene YAML read/write endpoints
including validation, content-type, and round-trip integrity.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Automation YAML ──────────────────────────────────────────

@pytest.mark.marge_only
async def test_automation_yaml_content_type(rest):
    """GET /api/config/automation/yaml returns text/yaml content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "yaml" in ct


async def test_automation_yaml_has_entries(rest):
    """Automation YAML contains at least 6 automation entries."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    text = resp.text
    # Count automation entries by counting "- id:" patterns
    count = text.count("- id:")
    assert count >= 6, f"Expected 6+ automations, found {count}"


@pytest.mark.marge_only
async def test_automation_yaml_roundtrip(rest):
    """Read YAML, write it back, read again — content matches."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    original = resp1.text

    # Write it back
    resp2 = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content=original,
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp2.status_code == 200

    # Read again
    resp3 = await rest.client.get(
        f"{rest.base_url}/api/config/automation/yaml",
        headers=rest._headers(),
    )
    assert resp3.text == original


@pytest.mark.marge_only
async def test_automation_yaml_invalid_rejected(rest):
    """PUT with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/automation/yaml",
        content="not: valid: automation: yaml: [[[",
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp.status_code == 400


# ── Scene YAML ───────────────────────────────────────────────

@pytest.mark.marge_only
async def test_scene_yaml_content_type(rest):
    """GET /api/config/scene/yaml returns text/yaml content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "yaml" in ct


async def test_scene_yaml_has_entries(rest):
    """Scene YAML contains at least 2 scene entries."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    text = resp.text
    count = text.count("- id:")
    assert count >= 2, f"Expected 2+ scenes, found {count}"


@pytest.mark.marge_only
async def test_scene_yaml_roundtrip(rest):
    """Read scene YAML, write it back, read again — content matches."""
    resp1 = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    original = resp1.text

    resp2 = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content=original,
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp2.status_code == 200

    resp3 = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp3.text == original


@pytest.mark.marge_only
async def test_scene_yaml_invalid_rejected(rest):
    """PUT with invalid scene YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content="this is not valid scene yaml [[[",
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp.status_code == 400
