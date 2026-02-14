"""
CTS -- Auth Token Lifecycle Tests

Tests long-lived access token CRUD operations:
create, list, fields, delete, and token validation.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_token_create(rest):
    """POST /api/auth/tokens creates a new token."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "auth_lc_test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "token" in data


async def test_token_list_contains_created(rest):
    """GET /api/auth/tokens lists created tokens."""
    # Create a token first
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "auth_lc_list_test"},
        headers=rest._headers(),
    )
    created = create_resp.json()

    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    tokens = resp.json()
    assert isinstance(tokens, list)
    ids = [t.get("id") for t in tokens]
    assert created["id"] in ids


async def test_token_list_fields(rest):
    """Token entries have name and created_at fields."""
    await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "auth_lc_fields"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    for token in tokens:
        assert "id" in token
        assert "name" in token
        assert "created_at" in token


async def test_token_delete(rest):
    """DELETE /api/auth/tokens/:id removes token."""
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "auth_lc_delete"},
        headers=rest._headers(),
    )
    token_id = create_resp.json()["id"]

    del_resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200

    # Verify not in list
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t.get("id") for t in resp.json()]
    assert token_id not in ids


async def test_token_delete_nonexistent(rest):
    """DELETE /api/auth/tokens/:id for missing token returns 404."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/nonexistent_id_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_token_create_unique_ids(rest):
    """Multiple token creates produce unique IDs."""
    ids = set()
    for i in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/auth/tokens",
            json={"name": f"auth_lc_unique_{i}"},
            headers=rest._headers(),
        )
        ids.add(resp.json()["id"])
    assert len(ids) == 3


async def test_token_has_secret(rest):
    """Created token includes the secret value."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "auth_lc_secret"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert len(data["token"]) > 0
