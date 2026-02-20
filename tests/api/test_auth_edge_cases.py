"""
CTS -- Authentication and Token Management Tests

Tests open-mode auth behavior (MARGE_AUTH_TOKEN not set), long-lived
access token CRUD, and endpoint accessibility.
"""

import uuid
import pytest
import httpx

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]

BASE = "http://localhost:8124"


# ── Open-mode access tests (no MARGE_AUTH_TOKEN) ──────────

async def test_open_mode_no_header_allowed():
    """Without MARGE_AUTH_TOKEN, requests without auth succeed."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/states")
        assert r.status_code == 200


async def test_open_mode_arbitrary_bearer_allowed():
    """Without MARGE_AUTH_TOKEN, any Bearer token succeeds."""
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{BASE}/api/states",
            headers={"Authorization": "Bearer anything-goes"},
        )
        assert r.status_code == 200


async def test_open_mode_empty_header_allowed():
    """Without MARGE_AUTH_TOKEN, empty auth header succeeds."""
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{BASE}/api/states",
            headers={"Authorization": ""},
        )
        assert r.status_code == 200


async def test_open_mode_config_accessible():
    """GET /api/config accessible without auth in open mode."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data


async def test_open_mode_services_accessible():
    """POST /api/services accessible without auth in open mode."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.auth_open_{tag}"
    # Pre-create entity
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{BASE}/api/states/{eid}",
            json={"state": "off"},
        )
        r = await c.post(
            f"{BASE}/api/services/light/turn_on",
            json={"entity_id": eid},
        )
        assert r.status_code == 200


async def test_health_endpoint_always_accessible():
    """GET /api/health is always accessible."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/api/health")
        assert r.status_code == 200


# ── Long-lived access token CRUD ──────────────────────────

async def test_create_token(rest):
    """POST /api/auth/tokens creates a new token."""
    name = f"test_token_{uuid.uuid4().hex[:8]}"
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": name},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == name
    assert "id" in data
    assert "token" in data
    assert data["token"].startswith("marge_")
    assert "created_at" in data


async def test_create_token_missing_name(rest):
    """POST /api/auth/tokens without name returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_list_tokens(rest):
    """GET /api/auth/tokens returns token list."""
    # Create a token first
    name = f"list_test_{uuid.uuid4().hex[:8]}"
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": name},
        headers=rest._headers(),
    )
    assert create_resp.status_code == 200

    # List tokens
    resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    # Find our token in the list
    names = [t["name"] for t in data]
    assert name in names

    # Token values should NOT be exposed in listings
    for token_info in data:
        assert token_info.get("token") is None


async def test_delete_token(rest):
    """DELETE /api/auth/tokens/{id} removes the token."""
    name = f"delete_test_{uuid.uuid4().hex[:8]}"
    create_resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": name},
        headers=rest._headers(),
    )
    data = create_resp.json()
    token_id = data["id"]

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/{token_id}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify removed from list
    list_resp = await rest.client.get(
        f"{rest.base_url}/api/auth/tokens",
        headers=rest._headers(),
    )
    ids = [t["id"] for t in list_resp.json()]
    assert token_id not in ids


async def test_delete_nonexistent_token(rest):
    """DELETE /api/auth/tokens/{id} with bad id returns 404."""
    resp = await rest.client.delete(
        f"{rest.base_url}/api/auth/tokens/nonexistent_xyz",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_created_token_has_correct_format(rest):
    """Created token starts with 'marge_' prefix."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": f"fmt_test_{uuid.uuid4().hex[:8]}"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["token"].startswith("marge_")
    # Token should be a UUID-based string (32 hex chars after prefix)
    assert len(data["token"]) == 6 + 32  # "marge_" + 32 hex


async def test_token_id_has_correct_format(rest):
    """Token ID starts with 'tok_' prefix."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/auth/tokens",
        json={"name": f"id_test_{uuid.uuid4().hex[:8]}"},
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["id"].startswith("tok_")
