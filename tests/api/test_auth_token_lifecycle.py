"""
CTS -- Auth Token Lifecycle Tests

Tests long-lived access token CRUD via REST API:
create, list, delete, token format validation, and full lifecycle.
"""

import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


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


async def test_create_token(rest):
    """POST /api/auth/tokens creates a token with name."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"CTS Test Token {tag}")
    assert data["name"] == f"CTS Test Token {tag}"
    assert "id" in data
    assert data["id"].startswith("tok_")
    assert "token" in data
    assert data["token"].startswith("marge_")
    assert "created_at" in data


async def test_list_tokens(rest):
    """GET /api/auth/tokens returns token list containing created token."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"List Test Token {tag}")

    tokens = await _list_tokens(rest)
    assert isinstance(tokens, list)
    # Token should appear in listing
    ids = [t["id"] for t in tokens]
    assert created["id"] in ids


async def test_list_tokens_hides_value(rest):
    """Token listing does not expose token values."""
    tag = uuid.uuid4().hex[:8]
    await _create_token(rest, f"Hidden Value Token {tag}")

    tokens = await _list_tokens(rest)
    for tok in tokens:
        assert tok.get("token") is None, "Token value should not be exposed in listing"


async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{id} removes a token."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"Delete Me Token {tag}")
    token_id = created["id"]

    resp = await _delete_token(rest, token_id)
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"

    # Verify it's gone from listing
    tokens = await _list_tokens(rest)
    ids = [t["id"] for t in tokens]
    assert token_id not in ids


async def test_delete_nonexistent_token_404(rest):
    """DELETE /api/auth/tokens/{bad_id} returns 404."""
    resp = await _delete_token(rest, "tok_nonexistent_xyz_99")
    assert resp.status_code == 404


async def test_create_token_missing_name_400(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("field,prefix,min_len", [
    ("id", "tok_", 10),
    ("token", "marge_", 10),
])
async def test_token_field_format(rest, field, prefix, min_len):
    """Token fields follow expected prefix format."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"Format Check {tag}")
    assert data[field].startswith(prefix)
    assert len(data[field]) > min_len


async def test_multiple_tokens_unique_ids(rest):
    """Multiple tokens have unique IDs and values."""
    tokens = []
    for i in range(3):
        tag = uuid.uuid4().hex[:8]
        data = await _create_token(rest, f"Multi Token {i} {tag}")
        tokens.append(data)

    ids = [t["id"] for t in tokens]
    values = [t["token"] for t in tokens]
    assert len(set(ids)) == 3, "Token IDs should be unique"
    assert len(set(values)) == 3, "Token values should be unique"


async def test_token_has_created_at(rest):
    """Token created_at is an ISO timestamp."""
    tag = uuid.uuid4().hex[:8]
    data = await _create_token(rest, f"Timestamp Token {tag}")
    assert "T" in data["created_at"]
    assert "20" in data["created_at"]


# ── Listed Token Fields (from depth) ──────────────────


async def test_listed_token_has_name(rest):
    """Listed tokens have name field matching creation name."""
    tag = uuid.uuid4().hex[:8]
    name = f"named_{tag}"
    created = await _create_token(rest, name)
    tokens = await _list_tokens(rest)
    token = next(t for t in tokens if t["id"] == created["id"])
    assert token["name"] == name


# ── Full Lifecycle (from depth) ────────────────────────


async def test_token_full_lifecycle(rest):
    """Token: create -> list -> verify -> delete -> confirm gone."""
    tag = uuid.uuid4().hex[:8]
    created = await _create_token(rest, f"life_{tag}")

    tokens = await _list_tokens(rest)
    assert any(t["id"] == created["id"] for t in tokens)

    resp = await _delete_token(rest, created["id"])
    assert resp.status_code == 200

    tokens = await _list_tokens(rest)
    assert not any(t["id"] == created["id"] for t in tokens)


# ── Merged from test_auth_lifecycle.py ─────────────────


async def test_listed_tokens_have_all_fields(rest):
    """All listed tokens have id, name, and created_at fields."""
    tag = uuid.uuid4().hex[:8]
    await _create_token(rest, f"fields_check_{tag}")

    tokens = await _list_tokens(rest)
    for token in tokens:
        assert "id" in token
        assert "name" in token
        assert "created_at" in token
