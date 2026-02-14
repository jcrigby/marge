"""
CTS -- REST Backup Endpoint Depth Tests

Tests GET /api/backup endpoint: response format, backup file
creation, content-type, and gzip validation.
"""

import pytest

pytestmark = pytest.mark.asyncio


# ── Backup Endpoint ──────────────────────────────────────

async def test_backup_returns_200(rest):
    """GET /api/backup returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_backup_returns_binary(rest):
    """GET /api/backup returns binary content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert len(resp.content) > 0


async def test_backup_has_content_type(rest):
    """GET /api/backup sets content-type header."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    ct = resp.headers.get("content-type", "")
    assert "gzip" in ct or "octet" in ct or "tar" in ct


async def test_backup_content_starts_with_gzip_magic(rest):
    """Backup content starts with gzip magic bytes (1f 8b)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    content = resp.content
    assert len(content) >= 2
    assert content[0] == 0x1F and content[1] == 0x8B


async def test_backup_has_content_disposition(rest):
    """GET /api/backup sets content-disposition header."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "marge" in cd.lower()
