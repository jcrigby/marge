"""
CTS -- Service Call Performance Depth Tests

Tests service call throughput across multiple domains: sequential
multi-domain calls, concurrent same-domain calls, concurrent
cross-domain calls, and service response format validation.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Sequential Multi-Domain ──────────────────────────────

async def test_sequential_multi_domain_services(rest):
    """Sequential service calls across 5 domains all succeed."""
    tag = uuid.uuid4().hex[:8]
    domains = [
        ("light", f"light.scp_seq_{tag}", "turn_on"),
        ("switch", f"switch.scp_seq_{tag}", "turn_on"),
        ("lock", f"lock.scp_seq_{tag}", "lock"),
        ("cover", f"cover.scp_seq_{tag}", "open_cover"),
        ("fan", f"fan.scp_seq_{tag}", "turn_on"),
    ]
    for domain, eid, _ in domains:
        await rest.set_state(eid, "off")

    for domain, eid, service in domains:
        await rest.call_service(domain, service, {"entity_id": eid})

    # Verify all changed
    expected = {
        f"light.scp_seq_{tag}": "on",
        f"switch.scp_seq_{tag}": "on",
        f"lock.scp_seq_{tag}": "locked",
        f"cover.scp_seq_{tag}": "open",
        f"fan.scp_seq_{tag}": "on",
    }
    for eid, exp_state in expected.items():
        state = await rest.get_state(eid)
        assert state["state"] == exp_state


async def test_sequential_service_throughput(rest):
    """Sequential service calls achieve >50 ops/s."""
    tag = uuid.uuid4().hex[:8]
    for i in range(20):
        await rest.set_state(f"switch.scp_sthr_{i}_{tag}", "off")

    t0 = time.monotonic()
    for i in range(20):
        await rest.call_service("switch", "turn_on", {
            "entity_id": f"switch.scp_sthr_{i}_{tag}",
        })
    elapsed = time.monotonic() - t0
    throughput = 20 / elapsed
    assert throughput > 50, f"Sequential service throughput {throughput:.0f} ops/s below 50"


# ── Concurrent Same-Domain ────────────────────────────────

async def test_concurrent_light_services(rest):
    """20 concurrent light service calls all succeed."""
    tag = uuid.uuid4().hex[:8]
    for i in range(20):
        await rest.set_state(f"light.scp_clight_{i}_{tag}", "off")

    tasks = [
        rest.call_service("light", "turn_on", {
            "entity_id": f"light.scp_clight_{i}_{tag}",
        })
        for i in range(20)
    ]
    await asyncio.gather(*tasks)

    for i in range(20):
        state = await rest.get_state(f"light.scp_clight_{i}_{tag}")
        assert state["state"] == "on"


async def test_concurrent_service_throughput(rest):
    """Concurrent service calls achieve >100 ops/s."""
    tag = uuid.uuid4().hex[:8]
    for i in range(30):
        await rest.set_state(f"switch.scp_cthr_{i}_{tag}", "off")

    t0 = time.monotonic()
    tasks = [
        rest.call_service("switch", "turn_on", {
            "entity_id": f"switch.scp_cthr_{i}_{tag}",
        })
        for i in range(30)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 30 / elapsed
    assert throughput > 100, f"Concurrent service throughput {throughput:.0f} ops/s below 100"


# ── Concurrent Cross-Domain ──────────────────────────────

async def test_concurrent_cross_domain_services(rest):
    """Concurrent service calls across different domains succeed."""
    tag = uuid.uuid4().hex[:8]
    entities = {
        "light": [f"light.scp_xd_{i}_{tag}" for i in range(5)],
        "switch": [f"switch.scp_xd_{i}_{tag}" for i in range(5)],
        "lock": [f"lock.scp_xd_{i}_{tag}" for i in range(5)],
    }

    for eids in entities.values():
        for eid in eids:
            await rest.set_state(eid, "off")

    tasks = []
    for eid in entities["light"]:
        tasks.append(rest.call_service("light", "turn_on", {"entity_id": eid}))
    for eid in entities["switch"]:
        tasks.append(rest.call_service("switch", "turn_on", {"entity_id": eid}))
    for eid in entities["lock"]:
        tasks.append(rest.call_service("lock", "lock", {"entity_id": eid}))

    await asyncio.gather(*tasks)

    for eid in entities["light"]:
        assert (await rest.get_state(eid))["state"] == "on"
    for eid in entities["switch"]:
        assert (await rest.get_state(eid))["state"] == "on"
    for eid in entities["lock"]:
        assert (await rest.get_state(eid))["state"] == "locked"


# ── Service with Data Throughput ──────────────────────────

async def test_service_with_data_throughput(rest):
    """Service calls with data payloads achieve >50 ops/s."""
    tag = uuid.uuid4().hex[:8]
    for i in range(20):
        await rest.set_state(f"light.scp_data_{i}_{tag}", "off")

    t0 = time.monotonic()
    tasks = [
        rest.call_service("light", "turn_on", {
            "entity_id": f"light.scp_data_{i}_{tag}",
            "brightness": 128 + i,
            "color_temp": 300,
        })
        for i in range(20)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 20 / elapsed
    assert throughput > 50, f"Data service throughput {throughput:.0f} ops/s below 50"


# ── Toggle Cycle Throughput ──────────────────────────────

async def test_toggle_cycle_throughput(rest):
    """Rapid toggle cycles achieve >50 ops/s."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.scp_toggle_{tag}"
    await rest.set_state(eid, "off")

    t0 = time.monotonic()
    for _ in range(20):
        await rest.call_service("switch", "toggle", {"entity_id": eid})
    elapsed = time.monotonic() - t0
    throughput = 20 / elapsed
    assert throughput > 50, f"Toggle throughput {throughput:.0f} ops/s below 50"
