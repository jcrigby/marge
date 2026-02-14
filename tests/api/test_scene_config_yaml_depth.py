"""
CTS -- Scene Config and YAML Roundtrip Depth Tests

Tests GET /api/config/scene/config metadata, GET/PUT scene YAML
roundtrip, and scene entity listings.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Scene Config Listing ──────────────────────────────────

async def test_scene_config_list(rest):
    """GET /api/config/scene/config returns scene list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # evening + goodnight


async def test_scene_config_has_fields(rest):
    """Each scene has id, name, entity_count fields."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "id" in scene
        assert "name" in scene
        assert "entity_count" in scene


async def test_scene_evening_config(rest):
    """Evening scene has 5 entities (4 lights + media_player)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    evening = next((s for s in data if "evening" in s.get("name", "").lower() or "evening" in s.get("id", "")), None)
    assert evening is not None
    assert evening["entity_count"] == 5


async def test_scene_goodnight_config(rest):
    """Goodnight scene has 9 entities (all lights off)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    goodnight = next((s for s in data if "goodnight" in s.get("name", "").lower() or "goodnight" in s.get("id", "")), None)
    assert goodnight is not None
    assert goodnight["entity_count"] == 9


async def test_scene_config_has_entities_list(rest):
    """Scene config includes entities array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "entities" in scene
        assert isinstance(scene["entities"], list)


# ── Scene YAML GET/PUT ────────────────────────────────────

async def test_scene_yaml_get(rest):
    """GET /api/config/scene/yaml returns YAML text."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "name" in resp.text
    assert "entities" in resp.text


async def test_scene_yaml_content_type(rest):
    """Scene YAML response has text/yaml content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "yaml" in content_type


async def test_scene_yaml_roundtrip(rest):
    """GET scene YAML then PUT it back succeeds."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    yaml_text = resp.text

    put_resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content=yaml_text,
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data["result"] == "ok"


async def test_scene_yaml_put_invalid(rest):
    """PUT invalid scene YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content="not: valid: scene: yaml: [[[",
        headers={**rest._headers(), "content-type": "text/yaml"},
    )
    assert resp.status_code == 400


async def test_scene_yaml_contains_evening(rest):
    """Scene YAML includes evening scene definition."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "evening" in resp.text.lower()


async def test_scene_yaml_contains_goodnight(rest):
    """Scene YAML includes goodnight scene definition."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "goodnight" in resp.text.lower()
