"""
CTS -- Concurrent Read Throughput Depth Tests

Tests read performance: parallel GET /api/states, parallel individual
entity reads, mixed read+write throughput, and read consistency
under concurrent access.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Parallel Bulk Reads ──────────────────────────────────

async def test_concurrent_get_states(rest):
    """20 concurrent GET /api/states calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    await rest.set_state(f"sensor.cread_{tag}", "seed")

    tasks = [rest.get_states() for _ in range(20)]
    results = await asyncio.gather(*tasks)
    for r in results:
        assert isinstance(r, list)
        assert len(r) >= 1


async def test_concurrent_get_states_throughput(rest):
    """Concurrent GET /api/states achieves >10 ops/s."""
    t0 = time.monotonic()
    tasks = [rest.get_states() for _ in range(20)]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 20 / elapsed
    assert throughput > 10, f"Bulk read throughput {throughput:.0f} ops/s below 10"


# ── Parallel Individual Entity Reads ──────────────────────

async def test_concurrent_individual_reads(rest):
    """50 concurrent individual entity reads all return correct values."""
    tag = uuid.uuid4().hex[:8]
    for i in range(50):
        await rest.set_state(f"sensor.cread_ind_{i}_{tag}", str(i * 3))

    tasks = [
        rest.get_state(f"sensor.cread_ind_{i}_{tag}")
        for i in range(50)
    ]
    results = await asyncio.gather(*tasks)
    for i, state in enumerate(results):
        assert state["state"] == str(i * 3)


async def test_individual_read_throughput(rest):
    """Individual entity reads achieve >500 ops/s."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_thr_{tag}"
    await rest.set_state(eid, "42")

    t0 = time.monotonic()
    tasks = [rest.get_state(eid) for _ in range(100)]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 100 / elapsed
    assert throughput > 500, f"Individual read throughput {throughput:.0f} ops/s below 500"


# ── Mixed Read + Write ───────────────────────────────────

async def test_mixed_read_write_consistency(rest):
    """Interleaved reads and writes maintain consistency."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_mix_{tag}"
    await rest.set_state(eid, "0")

    # Write new values and read in sequence
    for i in range(10):
        await rest.set_state(eid, str(i))
        state = await rest.get_state(eid)
        assert state["state"] == str(i)


async def test_concurrent_read_during_writes(rest):
    """Reads during concurrent writes return valid states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_rw_{tag}"
    await rest.set_state(eid, "start")

    async def writer():
        for i in range(20):
            await rest.set_state(eid, str(i))

    async def reader():
        results = []
        for _ in range(20):
            state = await rest.get_state(eid)
            results.append(state["state"])
        return results

    _, read_results = await asyncio.gather(writer(), reader())
    # All reads should return valid string states
    for r in read_results:
        assert isinstance(r, str)


async def test_mixed_throughput(rest):
    """Mixed read+write operations achieve >200 ops/s."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_mxt_{tag}"
    await rest.set_state(eid, "0")

    t0 = time.monotonic()
    tasks = []
    for i in range(50):
        if i % 2 == 0:
            tasks.append(rest.set_state(eid, str(i)))
        else:
            tasks.append(rest.get_state(eid))
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 50 / elapsed
    assert throughput > 200, f"Mixed throughput {throughput:.0f} ops/s below 200"


# ── Read Consistency ──────────────────────────────────────

async def test_read_after_delete_returns_404(rest):
    """Reading deleted entity returns 404."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_del_{tag}"
    await rest.set_state(eid, "exists")

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


async def test_read_nonexistent_returns_404(rest):
    """Reading never-created entity returns 404."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.cread_noex_{tag}"
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404
