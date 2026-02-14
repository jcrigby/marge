"""
CTS -- Auth Token API Depth Tests

Tests the auth token REST API: create tokens, list tokens, delete tokens,
and validate that created tokens appear/disappear from the list.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Create Token ──────────────────────────────────────────

async def test_create_token(rest):
    """POST /api/auth/tokens creates a new token."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"test_token_{tag}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "name" in data
    assert data["name"] == f"test_token_{tag}"


async def test_create_token_has_token_value(rest):
    """Created token response includes the token value."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_val_{tag}"},
    )
    data = resp.json()
    assert "token" in data
    assert data["token"] is not None
    assert data["token"].startswith("marge_")


async def test_create_token_has_created_at(rest):
    """Created token has created_at timestamp."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_ts_{tag}"},
    )
    data = resp.json()
    assert "created_at" in data


async def test_create_token_has_id(rest):
    """Created token has a tok_ prefixed ID."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_id_{tag}"},
    )
    data = resp.json()
    assert data["id"].startswith("tok_")


# ── List Tokens ───────────────────────────────────────────

async def test_list_tokens(rest):
    """GET /api/auth/tokens returns a list."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_created_token_in_list(rest):
    """Created token appears in the token list."""
    tag = uuid.uuid4().hex[:8]
    name = f"tok_list_{tag}"
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": name},
    )
    token_id = create_resp.json()["id"]
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t["id"] for t in list_resp.json()]
    assert token_id in ids


async def test_listed_token_hides_value(rest):
    """Listed tokens don't expose the token value."""
    tag = uuid.uuid4().hex[:8]
    await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_hide_{tag}"},
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    for token in resp.json():
        # Token value should be None or absent in list
        assert token.get("token") is None


# ── Delete Token ──────────────────────────────────────────

async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{token_id} removes the token."""
    tag = uuid.uuid4().hex[:8]
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_del_{tag}"},
    )
    token_id = create_resp.json()["id"]
    del_resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert del_resp.status_code == 200


async def test_deleted_token_gone_from_list(rest):
    """Deleted token no longer appears in list."""
    tag = uuid.uuid4().hex[:8]
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={"name": f"tok_gone_{tag}"},
    )
    token_id = create_resp.json()["id"]
    await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t["id"] for t in list_resp.json()]
    assert token_id not in ids


# ── Create Token Missing Name ─────────────────────────────

async def test_create_token_no_name_400(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code in (400, 422)
