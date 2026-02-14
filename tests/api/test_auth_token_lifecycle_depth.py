"""
CTS -- Auth Token Lifecycle Depth Tests

Tests the long-lived access token REST API: create token, list tokens,
verify token has expected fields, delete token. Covers the full
lifecycle and edge cases.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_token(rest, name):
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _list_tokens(rest):
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _delete_token(rest, token_id):
    return await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )


# ── Create ────────────────────────────────────────────────

async def test_create_token(rest):
    """POST /api/auth/tokens creates a new token."""
    tag = uuid.uuid4().hex[:8]
    token = await _create_token(rest, f"test_{tag}")
    assert "id" in token
    assert "name" in token
    assert token["name"] == f"test_{tag}"


async def test_create_token_has_token_value(rest):
    """Created token response includes the token value (shown once)."""
    tag = uuid.uuid4().hex[:8]
    token = await _create_token(rest, f"tok_{tag}")
    assert "token" in token
    assert token["token"] is not None
    assert token["token"].startswith("marge_")


async def test_create_token_has_id(rest):
    """Created token has id starting with tok_."""
    tag = uuid.uuid4().hex[:8]
    token = await _create_token(rest, f"id_{tag}")
    assert token["id"].startswith("tok_")


async def test_create_token_has_created_at(rest):
    """Created token has created_at timestamp."""
    tag = uuid.uuid4().hex[:8]
    token = await _create_token(rest, f"ts_{tag}")
    assert "created_at" in token


# ── List ──────────────────────────────────────────────────

async def test_list_tokens(rest):
    """GET /api/auth/tokens returns a list."""
    tokens = await _list_tokens(rest)
    assert isinstance(tokens, list)


async def test_created_token_in_list(rest):
    """Created token appears in token list."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"list_{tag}")
    tokens = await _list_tokens(rest)
    ids = [t["id"] for t in tokens]
    assert created["id"] in ids


async def test_listed_token_has_name(rest):
    """Listed tokens have name field."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"named_{tag}")
    tokens = await _list_tokens(rest)
    token = next(t for t in tokens if t["id"] == created["id"])
    assert token["name"] == f"named_{tag}"


# ── Delete ────────────────────────────────────────────────

async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{id} removes the token."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"del_{tag}")
    resp = await _delete_token(rest, created["id"])
    assert resp.status_code == 200
    tokens = await _list_tokens(rest)
    ids = [t["id"] for t in tokens]
    assert created["id"] not in ids


async def test_delete_nonexistent_token_returns_404(rest):
    """DELETE on non-existent token returns 404."""
    resp = await _delete_token(rest, "tok_nonexistent_xyz_99")
    assert resp.status_code == 404


# ── Full Lifecycle ────────────────────────────────────────

async def test_token_full_lifecycle(rest):
    """Token: create → list → verify → delete → confirm gone."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"life_{tag}")

    tokens = await _list_tokens(rest)
    assert any(t["id"] == created["id"] for t in tokens)

    resp = await _delete_token(rest, created["id"])
    assert resp.status_code == 200

    tokens = await _list_tokens(rest)
    assert not any(t["id"] == created["id"] for t in tokens)
