"""
CTS -- Long-Lived Access Token Tests

Tests the /api/auth/tokens CRUD endpoints for creating,
listing, and deleting long-lived access tokens.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_tokens_returns_list(rest):
    """GET /api/auth/tokens returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_create_token(rest):
    """POST /api/auth/tokens creates a new token and returns it."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "CTS Test Token"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["name"] == "CTS Test Token"
    assert "token" in body  # Token value shown on creation
    assert body["token"].startswith("marge_")
    assert "created_at" in body

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{body['id']}",
        headers=rest._headers(),
    )


async def test_create_token_appears_in_list(rest):
    """Created token appears in GET /api/auth/tokens list."""
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "List Verification Token"},
        headers=rest._headers(),
    )
    body = resp.json()
    token_id = body["id"]

    # List
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    ids = [t["id"] for t in tokens]
    assert token_id in ids

    # Token value NOT exposed in listing
    match = next(t for t in tokens if t["id"] == token_id)
    assert match.get("token") is None

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )


async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{id} removes the token."""
    # Create
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Delete Me Token"},
        headers=rest._headers(),
    )
    body = resp.json()
    token_id = body["id"]

    # Delete
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify gone
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t["id"] for t in resp.json()]
    assert token_id not in ids


async def test_delete_nonexistent_token_returns_404(rest):
    """DELETE for nonexistent token returns 404."""
    resp = await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/tok_does_not_exist",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_create_token_missing_name_returns_400(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_create_multiple_tokens(rest):
    """Multiple tokens can be created and listed."""
    ids = []
    for i in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/auth/tokens",
            json={"name": f"Multi Token {i}"},
            headers=rest._headers(),
        )
        ids.append(resp.json()["id"])

    # List
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    listed_ids = [t["id"] for t in resp.json()]
    for tid in ids:
        assert tid in listed_ids

    # Cleanup
    for tid in ids:
        await rest.client.request(
            "DELETE",
            f"{rest.base_url}/api/auth/tokens/{tid}",
            headers=rest._headers(),
        )


async def test_token_id_format(rest):
    """Token IDs start with tok_ prefix."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": "Format Test"},
        headers=rest._headers(),
    )
    body = resp.json()
    assert body["id"].startswith("tok_")

    # Cleanup
    await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{body['id']}",
        headers=rest._headers(),
    )
