"""
CTS -- Backup and Error Log Endpoint Tests

Tests GET /api/backup archive integrity and GET /api/error_log behavior.
"""

import io
import gzip
import tarfile
import pytest

pytestmark = pytest.mark.asyncio


async def test_backup_returns_200(rest):
    """GET /api/backup returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_backup_content_type(rest):
    """Backup response has gzip content type."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    ct = resp.headers.get("content-type", "")
    assert "gzip" in ct


async def test_backup_content_disposition(rest):
    """Backup has Content-Disposition with filename."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "marge_backup_" in cd
    assert ".tar.gz" in cd


async def test_backup_is_valid_gzip(rest):
    """Backup data is valid gzip."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    gzip.decompress(resp.content)


async def test_backup_is_valid_tar(rest):
    """Backup is a valid tar.gz archive."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert isinstance(names, list)


async def test_backup_contains_database(rest):
    """Backup archive contains marge.db."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "marge.db" in names


async def test_backup_contains_automations(rest):
    """Backup archive contains automations.yaml."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "automations.yaml" in names


async def test_backup_contains_scenes(rest):
    """Backup archive contains scenes.yaml."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        names = tar.getnames()
        assert "scenes.yaml" in names


async def test_backup_database_not_empty(rest):
    """Database file in backup has non-zero size."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/backup",
        headers=rest._headers(),
    )
    buf = io.BytesIO(resp.content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        db_member = tar.getmember("marge.db")
        assert db_member.size > 0


# ── Error Log ─────────────────────────────────────────────

async def test_error_log_returns_200(rest):
    """GET /api/error_log returns 200."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_error_log_returns_string(rest):
    """Error log response is a string (possibly empty)."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/error_log",
        headers=rest._headers(),
    )
    assert isinstance(resp.text, str)
