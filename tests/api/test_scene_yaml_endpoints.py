"""
CTS -- Scene YAML Endpoint Tests

Tests GET /api/config/scene/yaml (read raw YAML), PUT /api/config/scene/yaml
(validate and save), and scene config metadata via GET /api/config/scene/config.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_scene_yaml_returns_200(rest):
    """GET /api/config/scene/yaml returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_get_scene_yaml_content_type(rest):
    """GET /api/config/scene/yaml returns text/yaml content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "text/yaml" in resp.headers.get("content-type", "")


async def test_get_scene_yaml_contains_scenes(rest):
    """Scene YAML contains scene definitions."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    yaml_text = resp.text
    assert "id:" in yaml_text or "name:" in yaml_text


async def test_get_scene_yaml_has_evening(rest):
    """Scene YAML references 'evening' scene."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "evening" in resp.text.lower()


async def test_get_scene_yaml_has_goodnight(rest):
    """Scene YAML references 'goodnight' scene."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert "goodnight" in resp.text.lower()


async def test_put_scene_yaml_invalid_returns_400(rest):
    """PUT /api/config/scene/yaml with invalid YAML returns 400."""
    resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content="not: valid: yaml: [[[",
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_put_scene_yaml_valid_roundtrip(rest):
    """GET scene YAML then PUT it back succeeds."""
    get_resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    original = get_resp.text

    put_resp = await rest.client.put(
        f"{rest.base_url}/api/config/scene/yaml",
        content=original,
        headers=rest._headers(),
    )
    assert put_resp.status_code == 200
    data = put_resp.json()
    assert data.get("result") == "ok"


async def test_scene_config_list_returns_200(rest):
    """GET /api/config/scene/config returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_scene_config_list_is_array(rest):
    """Scene config returns a JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_scene_config_has_at_least_two(rest):
    """At least 2 scenes (evening, goodnight) are configured."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 2


async def test_scene_config_entry_has_fields(rest):
    """Scene config entries have id, name, entity_count."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    for scene in data:
        assert "id" in scene
        assert "name" in scene
        assert "entity_count" in scene
