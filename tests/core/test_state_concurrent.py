"""
CTS -- State Machine Concurrent Operation Tests

Tests concurrent state reads and writes to verify correctness
under parallel access.
"""

import asyncio
import pytest

pytestmark = pytest.mark.asyncio


async def test_concurrent_writes_no_data_loss(rest):
    """Concurrent writes to different entities all persist."""
    n = 20
    tasks = []
    for i in range(n):
        tasks.append(rest.set_state(f"sensor.conc_w_{i}", str(i)))
    await asyncio.gather(*tasks)

    for i in range(n):
        state = await rest.get_state(f"sensor.conc_w_{i}")
        assert state is not None
        assert state["state"] == str(i)


async def test_concurrent_write_same_entity(rest):
    """Concurrent writes to same entity — last write wins."""
    tasks = []
    for i in range(10):
        tasks.append(rest.set_state("sensor.conc_same", str(i)))
    await asyncio.gather(*tasks)

    state = await rest.get_state("sensor.conc_same")
    # State should be one of the written values (0-9)
    assert state["state"] in [str(i) for i in range(10)]


async def test_concurrent_creates_and_get_all(rest):
    """Concurrent entity creation + get_all returns all."""
    n = 15
    tasks = []
    for i in range(n):
        tasks.append(rest.set_state(f"sensor.conc_all_{i}", str(i)))
    await asyncio.gather(*tasks)

    states = await rest.get_states()
    ids = {s["entity_id"] for s in states}
    for i in range(n):
        assert f"sensor.conc_all_{i}" in ids


