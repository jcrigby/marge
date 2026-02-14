"""
CTS -- REST Auth Token Management Depth Tests

Tests /api/auth/tokens endpoints: create token, list tokens,
delete token, and token validation behavior.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── List Tokens ─────────────────────────────────────────

async def test_list_tokens_returns_200(rest):
    """GET /api/auth/tokens returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_list_tokens_returns_array(rest):
    """GET /api/auth/tokens returns JSON array."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    data = resp.json()
    assert isinstance(data, list)


async def test_list_tokens_entry_has_id(rest):
    """Token entries have id field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    if len(tokens) > 0:
        assert "id" in tokens[0]


async def test_list_tokens_entry_has_name(rest):
    """Token entries have name field."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    if len(tokens) > 0:
        assert "name" in tokens[0]


# ── Create Token ────────────────────────────────────────

async def test_create_token_returns_200(rest):
    """POST /api/auth/tokens with name returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"test_client_{tag}"},
    )
    assert resp.status_code == 200


async def test_create_token_returns_token(rest):
    """POST /api/auth/tokens returns token in response."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"test_tkn_{tag}"},
    )
    data = resp.json()
    assert "token" in data


async def test_created_token_appears_in_list(rest):
    """Created token appears in GET /api/auth/tokens."""
    tag = uuid.uuid4().hex[:8]
    name = f"test_list_{tag}"
    await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": name},
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    tokens = resp.json()
    names = [t.get("name", "") for t in tokens]
    assert name in names


# ── Delete Token ────────────────────────────────────────

async def test_delete_token(rest):
    """DELETE /api/auth/tokens/<id> removes token."""
    tag = uuid.uuid4().hex[:8]
    name = f"test_del_{tag}"
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": name},
    )
    data = create_resp.json()
    token_id = data.get("id", "")

    del_resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200

    # Verify removed from listing
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t.get("id", "") for t in list_resp.json()]
    assert token_id not in ids
