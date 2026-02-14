"""
CTS -- Auth Token CRUD Depth Tests

Tests long-lived access token management: create/list/delete lifecycle,
token value format, name validation, token authentication, secret
visibility rules, independence of multiple tokens, and revocation.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def _create_token(rest, name):
    """Create a token and return the full response data."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _list_tokens(rest):
    """List all tokens."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    return resp.json()


async def _delete_token(rest, token_id):
    """Delete a token by ID."""
    return await rest.client.request(
        "DELETE",
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )


# ── Token Create Format ──────────────────────────────────

async def test_created_token_has_id_prefix(rest):
    """Created token ID starts with 'tok_'."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"depth_prefix_{tag}")
    assert data["id"].startswith("tok_")


async def test_created_token_value_prefix(rest):
    """Created token value starts with 'marge_'."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"depth_val_{tag}")
    assert data["token"].startswith("marge_")


async def test_created_token_has_name(rest):
    """Created token response includes the name."""
    tag = uuid.uuid4().hex[:8]
    name = f"depth_name_{tag}"
    data = await _create_token(rest, name)
    assert data["name"] == name


async def test_created_token_has_created_at(rest):
    """Created token response includes created_at timestamp."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"depth_ts_{tag}")
    assert "created_at" in data
    assert len(data["created_at"]) > 0


async def test_create_without_name_fails(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


# ── Token List Behavior ──────────────────────────────────

async def test_listed_tokens_hide_secret(rest):
    """Listed tokens do not expose the token value (secret)."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"depth_hide_{tag}")
    tokens = await _list_tokens(rest)
    found = next((t for t in tokens if t["id"] == created["id"]), None)
    assert found is not None
    # Listed tokens should not have the token value, or it should be null
    token_val = found.get("token")
    assert token_val is None or token_val == ""


async def test_list_returns_array(rest):
    """GET /api/auth/tokens returns an array."""
    tokens = await _list_tokens(rest)
    assert isinstance(tokens, list)


async def test_list_all_fields_present(rest):
    """Each listed token has id, name, created_at."""
    tag = uuid.uuid4().hex[:8]
    await _create_token(rest, f"depth_fields_{tag}")
    tokens = await _list_tokens(rest)
    for t in tokens:
        assert "id" in t
        assert "name" in t
        assert "created_at" in t


# ── Token Authentication ─────────────────────────────────

async def test_created_token_authenticates(rest):
    """A newly created token can authenticate API calls."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"depth_auth_{tag}")
    token_value = data["token"]

    # Use the new token to call GET /api/health (no auth required)
    # and GET /api/states (auth required)
    resp = await rest.client.get(
        f"{rest.base_url}/api/states",
        headers={"Authorization": f"Bearer {token_value}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_revoked_token_removed_from_list(rest):
    """A revoked token no longer appears in the token list."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"depth_revoke_{tag}")
    token_id = data["id"]

    # Delete (revoke) the token
    del_resp = await _delete_token(rest, token_id)
    assert del_resp.status_code == 200

    # Verify it's gone from the list
    tokens = await _list_tokens(rest)
    ids = [t["id"] for t in tokens]
    assert token_id not in ids


# ── Multiple Tokens ──────────────────────────────────────

async def test_multiple_tokens_unique_values(rest):
    """Multiple tokens have distinct token values."""
    tag = uuid.uuid4().hex[:8]
    tokens = set()
    for i in range(3):
        data = await _create_token(rest, f"depth_multi_{i}_{tag}")
        tokens.add(data["token"])
    assert len(tokens) == 3


async def test_delete_one_preserves_others(rest):
    """Deleting one token doesn't affect other tokens."""
    tag = uuid.uuid4().hex[:8]
    t1 = await _create_token(rest, f"depth_keep1_{tag}")
    t2 = await _create_token(rest, f"depth_del_{tag}")
    t3 = await _create_token(rest, f"depth_keep2_{tag}")

    # Delete t2
    await _delete_token(rest, t2["id"])

    # t1 and t3 still in list
    tokens = await _list_tokens(rest)
    ids = {t["id"] for t in tokens}
    assert t1["id"] in ids
    assert t2["id"] not in ids
    assert t3["id"] in ids


async def test_delete_nonexistent_returns_404(rest):
    """DELETE /api/auth/tokens/<bogus> returns 404."""
    resp = await _delete_token(rest, "tok_nonexistent_bogus_xyz")
    assert resp.status_code == 404
