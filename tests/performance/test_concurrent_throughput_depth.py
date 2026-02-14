"""
CTS -- Concurrent Throughput Depth Tests

Tests Marge's performance under concurrent load: parallel state writes,
concurrent service calls, burst template renders, and simultaneous
multi-domain operations.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Parallel State Writes ────────────────────────────────

async def test_parallel_writes_100(rest):
    """100 concurrent state writes complete without error."""
    tag = uuid.uuid4().hex[:8]
    tasks = [
        rest.set_state(f"sensor.pw_{i}_{tag}", str(i))
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)
    # All should succeed (no exceptions)
    assert len(results) == 100


async def test_parallel_writes_all_visible(rest):
    """All concurrently written states are readable after completion."""
    tag = uuid.uuid4().hex[:8]
    count = 50
    tasks = [
        rest.set_state(f"sensor.pv_{i}_{tag}", str(i * 10))
        for i in range(count)
    ]
    await asyncio.gather(*tasks)
    # Verify all are present
    for i in range(count):
        state = await rest.get_state(f"sensor.pv_{i}_{tag}")
        assert state is not None
        assert state["state"] == str(i * 10)


# ── Concurrent Service Calls ─────────────────────────────

async def test_concurrent_turn_on(rest):
    """50 concurrent turn_on calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.ct_{i}_{tag}" for i in range(50)]
    # Create all entities
    await asyncio.gather(*[rest.set_state(eid, "off") for eid in eids])
    # Turn all on concurrently
    tasks = [
        rest.call_service("light", "turn_on", {"entity_id": eid})
        for eid in eids
    ]
    await asyncio.gather(*tasks)
    # Verify all on
    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


async def test_concurrent_toggle(rest):
    """Concurrent toggles all complete (final state may vary per timing)."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.ctog_{i}_{tag}" for i in range(20)]
    await asyncio.gather(*[rest.set_state(eid, "off") for eid in eids])
    tasks = [
        rest.call_service("switch", "toggle", {"entity_id": eid})
        for eid in eids
    ]
    await asyncio.gather(*tasks)
    # Each should have toggled exactly once: off → on
    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Burst Template Renders ───────────────────────────────

async def test_burst_template_renders(rest):
    """50 concurrent template renders complete."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_burst_{tag}"
    await rest.set_state(eid, "42")
    tasks = [
        rest.client.post(
            f"{rest.base_url}/api/template",
            json={"template": f"{{{{ states('{eid}') | int + {i} }}}}"},
            headers=rest._headers(),
        )
        for i in range(50)
    ]
    responses = await asyncio.gather(*tasks)
    for i, resp in enumerate(responses):
        assert resp.status_code == 200
        assert str(42 + i) in resp.text


# ── Multi-Domain Concurrent Operations ───────────────────

async def test_multi_domain_concurrent(rest):
    """Concurrent operations across different domains."""
    tag = uuid.uuid4().hex[:8]
    ops = []

    # Light operations
    for i in range(10):
        eid = f"light.md_{i}_{tag}"
        ops.append(rest.set_state(eid, "off"))

    # Sensor operations
    for i in range(10):
        eid = f"sensor.md_{i}_{tag}"
        ops.append(rest.set_state(eid, str(i * 5)))

    # Switch operations
    for i in range(10):
        eid = f"switch.md_{i}_{tag}"
        ops.append(rest.set_state(eid, "on"))

    await asyncio.gather(*ops)

    # Verify all domains have correct states
    assert (await rest.get_state(f"light.md_0_{tag}"))["state"] == "off"
    assert (await rest.get_state(f"sensor.md_5_{tag}"))["state"] == "25"
    assert (await rest.get_state(f"switch.md_9_{tag}"))["state"] == "on"


# ── Write Throughput ─────────────────────────────────────

async def test_write_throughput_above_100(rest):
    """Write throughput exceeds 100 entities/second over HTTP."""
    tag = uuid.uuid4().hex[:8]
    count = 200
    t0 = time.monotonic()
    tasks = [
        rest.set_state(f"sensor.tp_{i}_{tag}", str(i))
        for i in range(count)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = count / elapsed
    assert throughput > 100, f"Throughput {throughput:.0f} ops/s below 100"


# ── Read Throughput ──────────────────────────────────────

async def test_read_throughput_above_100(rest):
    """Read throughput exceeds 100 reads/second over HTTP."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rtp_{tag}"
    await rest.set_state(eid, "42")
    count = 200
    t0 = time.monotonic()
    tasks = [rest.get_state(eid) for _ in range(count)]
    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = count / elapsed
    assert all(r is not None for r in results)
    assert throughput > 100, f"Throughput {throughput:.0f} reads/s below 100"


# ── Health Under Load ────────────────────────────────────

async def test_health_during_writes(rest):
    """Health endpoint responds while state writes are in progress."""
    tag = uuid.uuid4().hex[:8]

    async def background_writes():
        for i in range(50):
            await rest.set_state(f"sensor.hl_{i}_{tag}", str(i))

    write_task = asyncio.create_task(background_writes())
    # Check health while writes happen
    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    await write_task
