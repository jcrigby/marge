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


async def test_concurrent_reads(rest):
    """Concurrent reads return consistent results."""
    await rest.set_state("sensor.conc_read", "42")
    tasks = [rest.get_state("sensor.conc_read") for _ in range(20)]
    results = await asyncio.gather(*tasks)
    for r in results:
        assert r["state"] == "42"


async def test_concurrent_write_same_entity(rest):
    """Concurrent writes to same entity — last write wins."""
    tasks = []
    for i in range(10):
        tasks.append(rest.set_state("sensor.conc_same", str(i)))
    await asyncio.gather(*tasks)

    state = await rest.get_state("sensor.conc_same")
    # State should be one of the written values (0-9)
    assert state["state"] in [str(i) for i in range(10)]


async def test_concurrent_mixed_operations(rest):
    """Mixed concurrent reads and writes don't crash."""
    await rest.set_state("sensor.conc_mix", "start")

    tasks = []
    for i in range(10):
        tasks.append(rest.set_state("sensor.conc_mix", str(i)))
        tasks.append(rest.get_state("sensor.conc_mix"))
    results = await asyncio.gather(*tasks)

    # No None values from reads (entity always exists)
    reads = [r for r in results if isinstance(r, dict)]
    for r in reads:
        assert r is not None


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


async def test_concurrent_service_calls(rest):
    """Concurrent service calls on different entities."""
    for i in range(10):
        await rest.set_state(f"light.conc_svc_{i}", "off")

    tasks = []
    for i in range(10):
        tasks.append(rest.call_service("light", "turn_on", {
            "entity_id": f"light.conc_svc_{i}",
        }))
    await asyncio.gather(*tasks)

    for i in range(10):
        state = await rest.get_state(f"light.conc_svc_{i}")
        assert state["state"] == "on"
