"""
CTS -- Concurrent Mixed Service Call Depth Tests

Tests concurrent service calls mixing different domains, verifying
that concurrent operations across domains produce correct results
and maintain data integrity.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Concurrent Mixed Domain Calls ────────────────────────

async def test_concurrent_light_switch_lock(rest):
    """Concurrent service calls across light, switch, lock domains."""
    tag = uuid.uuid4().hex[:8]
    entities = {
        f"light.cmix_l_{tag}": ("light", "turn_on", "on"),
        f"switch.cmix_s_{tag}": ("switch", "turn_on", "on"),
        f"lock.cmix_k_{tag}": ("lock", "lock", "locked"),
    }
    for eid in entities:
        await rest.set_state(eid, "off")

    tasks = [
        rest.call_service(domain, service, {"entity_id": eid})
        for eid, (domain, service, _) in entities.items()
    ]
    await asyncio.gather(*tasks)

    for eid, (_, _, expected) in entities.items():
        state = await rest.get_state(eid)
        assert state["state"] == expected


async def test_concurrent_toggle_multiple_domains(rest):
    """Concurrent toggle across multiple domains."""
    tag = uuid.uuid4().hex[:8]
    entities = [
        (f"light.cmix_tl_{tag}", "light"),
        (f"switch.cmix_ts_{tag}", "switch"),
        (f"siren.cmix_tr_{tag}", "siren"),
    ]
    for eid, _ in entities:
        await rest.set_state(eid, "on")

    tasks = [
        rest.call_service(domain, "toggle", {"entity_id": eid})
        for eid, domain in entities
    ]
    await asyncio.gather(*tasks)

    for eid, _ in entities:
        state = await rest.get_state(eid)
        assert state["state"] == "off"


# ── Concurrent Set State + Service ───────────────────────

async def test_concurrent_set_and_service(rest):
    """Concurrent set_state and service calls."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"sensor.cmix_ss1_{tag}"
    eid2 = f"switch.cmix_ss2_{tag}"
    await rest.set_state(eid2, "off")

    tasks = [
        rest.set_state(eid1, "42"),
        rest.call_service("switch", "turn_on", {"entity_id": eid2}),
    ]
    await asyncio.gather(*tasks)

    s1 = await rest.get_state(eid1)
    s2 = await rest.get_state(eid2)
    assert s1["state"] == "42"
    assert s2["state"] == "on"


# ── Bulk Service Throughput ──────────────────────────────

async def test_mixed_domain_throughput(rest):
    """Mixed domain concurrent services achieve >50 ops/s."""
    tag = uuid.uuid4().hex[:8]
    entities = []
    for i in range(10):
        entities.append((f"light.cmix_bt_{i}_{tag}", "light", "turn_on"))
        entities.append((f"switch.cmix_bt_{i}_{tag}", "switch", "turn_on"))

    for eid, _, _ in entities:
        await rest.set_state(eid, "off")

    t0 = time.monotonic()
    tasks = [
        rest.call_service(domain, service, {"entity_id": eid})
        for eid, domain, service in entities
    ]
    await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = len(entities) / elapsed
    assert throughput > 50, f"Mixed throughput {throughput:.0f} ops/s below 50"


# ── Rapid State Toggles ─────────────────────────────────

async def test_rapid_toggle_correctness(rest):
    """10 rapid toggles produce correct final state (even count = original)."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.cmix_rt_{tag}"
    await rest.set_state(eid, "off")

    for _ in range(10):
        await rest.call_service("switch", "toggle", {"entity_id": eid})

    state = await rest.get_state(eid)
    # 10 toggles from off = off (even count)
    assert state["state"] == "off"


async def test_concurrent_same_entity_services(rest):
    """Concurrent services on same entity all complete."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.cmix_same_{tag}"
    await rest.set_state(eid, "off")

    # All turn_on with different brightness
    tasks = [
        rest.call_service("light", "turn_on", {
            "entity_id": eid, "brightness": 50 + i * 10,
        })
        for i in range(5)
    ]
    await asyncio.gather(*tasks)

    # Final state should be on (one of the calls wins)
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert "brightness" in state["attributes"]
