"""
CTS -- REST Sim Time Endpoint Depth Tests

Tests POST /api/sim/time endpoint for simulation time control.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_sim_time_returns_200(rest):
    """POST /api/sim/time returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "12:00:00"},
    )
    assert resp.status_code == 200


async def test_sim_time_morning(rest):
    """POST /api/sim/time with morning time."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "06:30:00"},
    )
    assert resp.status_code == 200


async def test_sim_time_evening(rest):
    """POST /api/sim/time with evening time."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "19:00:00"},
    )
    assert resp.status_code == 200


async def test_sim_time_midnight(rest):
    """POST /api/sim/time with midnight."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "00:00:00"},
    )
    assert resp.status_code == 200


async def test_sim_time_returns_json(rest):
    """POST /api/sim/time returns JSON response."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/sim/time",
        headers=rest._headers(),
        json={"time": "15:00:00"},
    )
    data = resp.json()
    assert isinstance(data, dict)
