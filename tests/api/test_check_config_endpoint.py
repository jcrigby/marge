"""
CTS -- Config Check Endpoint Tests

Tests POST /api/config/core/check_config for configuration validation,
verifying it returns valid/invalid results with error details.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_check_config_returns_200(rest):
    """POST /api/config/core/check_config returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_check_config_has_result_field(rest):
    """Response includes 'result' field."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "result" in data


async def test_check_config_valid_result(rest):
    """Normal config returns result='valid'."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["result"] == "valid"


async def test_check_config_has_errors_field(rest):
    """Response includes 'errors' field."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert "errors" in data


async def test_check_config_errors_null_when_valid(rest):
    """Valid config has errors=null."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    data = resp.json()
    assert data["errors"] is None


async def test_check_config_response_is_json(rest):
    """Response Content-Type is application/json."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert "application/json" in resp.headers.get("content-type", "")


async def test_check_config_idempotent(rest):
    """Multiple check_config calls return same result."""
    results = []
    for _ in range(3):
        resp = await rest.client.post(
            f"{rest.base_url}/api/config/core/check_config",
            headers=rest._headers(),
        )
        results.append(resp.json()["result"])
    assert all(r == "valid" for r in results)


async def test_check_config_after_reload(rest):
    """check_config returns valid after automation reload."""
    # Trigger reload first
    await rest.client.post(
        f"{rest.base_url}/api/config/core/reload",
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)

    resp = await rest.client.post(
        f"{rest.base_url}/api/config/core/check_config",
        headers=rest._headers(),
    )
    assert resp.json()["result"] == "valid"
