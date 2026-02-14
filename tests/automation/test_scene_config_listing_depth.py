"""
CTS -- Scene Config Listing Depth Tests

Tests GET /api/config/scene/config: field presence, scene count,
scene entity state consistency, and YAML endpoint accessibility.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Scene Listing ─────────────────────────────────────────

async def test_scene_list_returns_array(rest):
    """GET /api/config/scene/config returns an array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_scene_list_nonempty(rest):
    """Scene list has at least one entry (demo scenes loaded)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data) >= 1


# ── Entry Fields ──────────────────────────────────────────

async def test_scene_entry_has_id(rest):
    """Each scene entry has id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "id" in entry
        assert len(str(entry["id"])) > 0


async def test_scene_entry_has_name(rest):
    """Each scene entry has name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "name" in entry


async def test_scene_entry_has_entities(rest):
    """Each scene entry has entities field (list of entity IDs)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    for entry in resp.json():
        assert "entities" in entry
        assert isinstance(entry["entities"], list)


# ── Scene Entity IDs ─────────────────────────────────────

async def test_scene_entities_are_strings(rest):
    """Scene entity entries are string entity IDs."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/config",
        headers=rest._headers(),
    )
    scenes = resp.json()
    for scene in scenes:
        entities = scene["entities"]
        for eid in entities:
            assert isinstance(eid, str)
            assert "." in eid  # domain.name format


# ── Scene YAML Endpoint ──────────────────────────────────

async def test_scene_yaml_returns_yaml(rest):
    """GET /api/config/scene/yaml returns YAML content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # YAML content type
    ct = resp.headers.get("content-type", "")
    assert "yaml" in ct or "text" in ct


async def test_scene_yaml_nonempty(rest):
    """Scene YAML content is not empty."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/scene/yaml",
        headers=rest._headers(),
    )
    assert len(resp.text.strip()) > 0
