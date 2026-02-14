"""
CTS -- Backup & Error Log Endpoint Tests

Tests GET /api/backup (tar.gz archive download) and
GET /api/error_log (empty log response).
"""

import io
import gzip
import tarfile
import pytest

pytestmark = pytest.mark.asyncio


async def test_backup_returns_gzip(rest):
    """GET /api/backup returns gzip content-type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "gzip" in ct


async def test_backup_has_content_disposition(rest):
    """Backup response has attachment filename."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "marge_backup_" in cd
    assert ".tar.gz" in cd


async def test_backup_is_valid_targz(rest):
    """Backup data is a valid tar.gz archive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    data = resp.content
    assert len(data) > 0

    # Should be valid gzip
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
        decompressed = gz.read()
        assert len(decompressed) > 0


async def test_backup_contains_db(rest):
    """Backup archive contains marge.db."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    data = resp.content
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        names = tar.getnames()
        assert "marge.db" in names


async def test_backup_nonzero_size(rest):
    """Backup archive has meaningful size (not empty)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    # DB should have tables and data, so > 1KB
    assert len(resp.content) > 1024


async def test_error_log_returns_200(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_error_log_returns_string(rest):
    """GET /api/error_log returns text content."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    # Marge returns empty log (uses structured tracing)
    assert isinstance(resp.text, str)
