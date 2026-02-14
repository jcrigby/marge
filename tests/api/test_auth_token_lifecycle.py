"""
CTS -- Auth Token Lifecycle Tests

Tests long-lived access token CRUD via REST API:
create, list, delete, and token format validation.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_token(rest):
    """POST /api/auth/tokens creates a token with name."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "CTS Test Token"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "CTS Test Token"
    assert "id" in data
    assert data["id"].startswith("tok_")
    assert "token" in data
    assert data["token"].startswith("marge_")
    assert "created_at" in data


async def test_list_tokens(rest):
    """GET /api/auth/tokens returns token list."""
    # Create a token first
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "List Test Token"},
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
    # Token should appear in listing
    ids = [t["id"] for t in tokens]
    assert created["id"] in ids


async def test_list_tokens_hides_value(rest):
    """Token listing does not expose token values."""
    await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Hidden Value Token"},
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    for tok in tokens:
        assert tok.get("token") is None, "Token value should not be exposed in listing"


async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{id} removes a token."""
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Delete Me Token"},
        headers=rest._headers(),
    )
    token_id = create_resp.json()["id"]

    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"

    # Verify it's gone from listing
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t["id"] for t in list_resp.json()]
    assert token_id not in ids


async def test_delete_nonexistent_token_404(rest):
    """DELETE /api/auth/tokens/{bad_id} returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/tok_nonexistent",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_create_token_missing_name_400(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_token_id_format(rest):
    """Token IDs follow tok_ prefix format."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Format Check"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["id"].startswith("tok_")
    assert len(data["id"]) > 10  # tok_ + uuid


async def test_token_value_format(rest):
    """Token values follow marge_ prefix format."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Value Format"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["token"].startswith("marge_")
    assert len(data["token"]) > 10


async def test_multiple_tokens_unique_ids(rest):
    """Multiple tokens have unique IDs and values."""
    tokens = []
    for i in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/auth/tokens",
            json={"name": f"Multi Token {i}"},
            headers=rest._headers(),
        )
        tokens.append(resp.json())

    ids = [t["id"] for t in tokens]
    values = [t["token"] for t in tokens]
    assert len(set(ids)) == 3, "Token IDs should be unique"
    assert len(set(values)) == 3, "Token values should be unique"


async def test_token_has_created_at(rest):
    """Token created_at is an ISO timestamp."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Timestamp Token"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert "T" in data["created_at"]
    assert "20" in data["created_at"]
