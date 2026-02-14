"""
CTS -- State Write Throughput Depth Tests

Tests rapid state write performance: sequential writes, concurrent
writes, large attribute payloads, and verifies all writes are correctly
recorded after the burst completes.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Sequential Write Throughput ──────────────────────────

async def test_sequential_100_writes(rest):
    """100 sequential state writes all succeed."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.perf_seq_{tag}"
    for i in range(100):
        await rest.set_state(eid, str(i))
    state = await rest.get_state(eid)
    assert state["state"] == "99"


async def test_sequential_write_throughput(rest):
    """Sequential writes achieve >100 ops/s."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.perf_seqt_{tag}"
    t0 = time.monotonic()
    for i in range(100):
        await rest.set_state(eid, str(i))
    elapsed = time.monotonic() - t0
    throughput = 100 / elapsed
    assert throughput > 100, f"Sequential throughput {throughput:.0f} ops/s below 100"


# ── Concurrent Write Throughput ──────────────────────────

async def test_concurrent_50_different_entities(rest):
    """50 concurrent writes to different entities all succeed."""
    tag = uuid.uuid4().hex[:8]
    tasks = [
        rest.set_state(f"sensor.perf_conc_{i}_{tag}", str(i))
        for i in range(50)
    ]
    await asyncio.gather(*tasks)
    # Verify all entities
    for i in range(50):
        state = await rest.get_state(f"sensor.perf_conc_{i}_{tag}")
        assert state["state"] == str(i)


async def test_concurrent_write_throughput(rest):
    """Concurrent writes achieve >200 ops/s."""
    tag = uuid.uuid4().hex[:8]
    t0 = time.monotonic()
    tasks = [
        rest.set_state(f"sensor.perf_ct_{i}_{tag}", str(i))
        for i in range(100)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 100 / elapsed
    assert throughput > 200, f"Concurrent throughput {throughput:.0f} ops/s below 200"


# ── Large Attribute Payloads ─────────────────────────────

async def test_large_attributes_write(rest):
    """Writing entity with many attributes succeeds."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.perf_attrs_{tag}"
    attrs = {f"key_{i}": f"value_{i}" for i in range(50)}
    await rest.set_state(eid, "42", attrs)
    state = await rest.get_state(eid)
    assert state["state"] == "42"
    assert len(state["attributes"]) >= 50


async def test_nested_attributes_write(rest):
    """Writing entity with nested attributes succeeds."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.perf_nested_{tag}"
    attrs = {
        "config": {"a": 1, "b": [1, 2, 3]},
        "metadata": {"type": "test", "values": {"x": 10, "y": 20}},
    }
    await rest.set_state(eid, "1", attrs)
    state = await rest.get_state(eid)
    assert state["attributes"]["config"]["a"] == 1
    assert state["attributes"]["metadata"]["values"]["x"] == 10


# ── Write + Read Consistency ─────────────────────────────

async def test_rapid_write_read_consistency(rest):
    """Rapid write then immediate read returns correct value."""
    tag = uuid.uuid4().hex[:8]
    for i in range(20):
        eid = f"sensor.perf_wr_{i}_{tag}"
        await rest.set_state(eid, str(i * 7))
        state = await rest.get_state(eid)
        assert state["state"] == str(i * 7)


async def test_overwrite_consistency(rest):
    """Rapidly overwriting same entity returns final value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.perf_ow_{tag}"
    for i in range(50):
        await rest.set_state(eid, str(i))
    state = await rest.get_state(eid)
    assert state["state"] == "49"


# ── Service Call Throughput ──────────────────────────────

async def test_service_call_throughput(rest):
    """Service calls achieve >100 ops/s."""
    tag = uuid.uuid4().hex[:8]
    for i in range(20):
        await rest.set_state(f"light.perf_svc_{i}_{tag}", "off")

    t0 = time.monotonic()
    tasks = [
        rest.call_service("light", "turn_on", {
            "entity_id": f"light.perf_svc_{i}_{tag}",
        })
        for i in range(20)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 20 / elapsed
    assert throughput > 100, f"Service throughput {throughput:.0f} ops/s below 100"
