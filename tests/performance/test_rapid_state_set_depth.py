"""
CTS -- Rapid State Set Performance Depth Tests

Tests rapid entity state setting: sequential updates, batch
creation, and update throughput measurement.
"""

import uuid
import time
import pytest

pytestmark = pytest.mark.asyncio


async def test_rapid_100_state_updates(rest):
    """100 sequential state updates complete in <5s."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.rss_rapid_{tag}"
    await rest.set_state(eid, "0")

    start = time.monotonic()
    for i in range(100):
        await rest.set_state(eid, str(i))
    elapsed = time.monotonic() - start

    state = await rest.get_state(eid)
    assert state["state"] == "99"
    assert elapsed < 5.0


async def test_rapid_50_entity_creation(rest):
    """Create 50 unique entities in <5s."""
    tag = uuid.uuid4().hex[:8]

    start = time.monotonic()
    for i in range(50):
        eid = f"sensor.rss_create_{i}_{tag}"
        await rest.set_state(eid, str(i))
    elapsed = time.monotonic() - start

    assert elapsed < 5.0
    # Spot check last entity
    state = await rest.get_state(f"sensor.rss_create_49_{tag}")
    assert state["state"] == "49"


async def test_rapid_service_calls(rest):
    """50 service calls complete in <5s."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.rss_svc_{i}_{tag}" for i in range(10)]
    for eid in eids:
        await rest.set_state(eid, "off")

    start = time.monotonic()
    for _ in range(5):
        for eid in eids:
            await rest.call_service("switch", "toggle", {"entity_id": eid})
    elapsed = time.monotonic() - start

    assert elapsed < 5.0


async def test_concurrent_domain_operations(rest):
    """Mixed domain operations maintain consistency."""
    tag = uuid.uuid4().hex[:8]
    entities = {
        f"light.rss_mix_{tag}": ("off", "light", "turn_on"),
        f"switch.rss_mix_{tag}": ("off", "switch", "turn_on"),
        f"fan.rss_mix_{tag}": ("off", "fan", "turn_on"),
        f"lock.rss_mix_{tag}": ("unlocked", "lock", "lock"),
    }

    for eid, (initial, _, _) in entities.items():
        await rest.set_state(eid, initial)

    for eid, (_, domain, service) in entities.items():
        await rest.call_service(domain, service, {"entity_id": eid})

    expected = {
        f"light.rss_mix_{tag}": "on",
        f"switch.rss_mix_{tag}": "on",
        f"fan.rss_mix_{tag}": "on",
        f"lock.rss_mix_{tag}": "locked",
    }
    for eid, exp_state in expected.items():
        state = await rest.get_state(eid)
        assert state["state"] == exp_state
