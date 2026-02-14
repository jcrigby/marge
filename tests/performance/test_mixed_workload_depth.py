"""
CTS -- Mixed Workload Depth Tests

Tests Marge under mixed concurrent operations: simultaneous state reads,
writes, service calls, template renders, and search queries. Verifies
all operations complete correctly without interference.
"""

import asyncio
import time
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Reads and Writes Concurrent ────────────────────────────

async def test_reads_during_writes(rest):
    """State reads succeed while writes are in progress."""
    tag = uuid.uuid4().hex[:8]
    eid_read = f"sensor.mw_read_{tag}"
    await rest.set_state(eid_read, "baseline")

    async def do_writes():
        for i in range(20):
            await rest.set_state(f"sensor.mw_wr_{i}_{tag}", str(i))

    async def do_reads():
        results = []
        for _ in range(20):
            state = await rest.get_state(eid_read)
            results.append(state)
        return results

    write_task = asyncio.create_task(do_writes())
    read_results = await do_reads()
    await write_task

    # All reads should have succeeded
    assert all(r is not None for r in read_results)
    assert all(r["state"] == "baseline" for r in read_results)


# ── Services and Templates Concurrent ──────────────────────

async def test_services_and_templates_concurrent(rest):
    """Service calls and template renders succeed concurrently."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mw_st_{tag}"
    await rest.set_state(eid, "0")

    service_tasks = []
    template_tasks = []

    for i in range(10):
        svc_eid = f"light.mw_svc_{i}_{tag}"
        await rest.set_state(svc_eid, "off")
        service_tasks.append(
            rest.call_service("light", "turn_on", {"entity_id": svc_eid})
        )

    for i in range(10):
        template_tasks.append(
            rest.client.post(
                f"{rest.base_url}/api/template",
                json={"template": f"{{{{ states('{eid}') | int + {i} }}}}"},
                headers=rest._headers(),
            )
        )

    all_results = await asyncio.gather(*service_tasks, *template_tasks)

    # Service results should be non-None (they return dicts)
    for r in all_results[:10]:
        assert r is not None

    # Template results should be 200
    for r in all_results[10:]:
        assert r.status_code == 200


# ── Search During State Changes ────────────────────────────

async def test_search_during_writes(rest):
    """Search completes while state writes are happening."""
    tag = uuid.uuid4().hex[:8]

    async def background_writes():
        for i in range(30):
            await rest.set_state(f"sensor.mw_sw_{i}_{tag}", str(i))

    write_task = asyncio.create_task(background_writes())

    # Search while writes happen
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/search?domain=sensor",
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    await write_task


# ── Multi-Domain Mixed Operations ──────────────────────────

async def test_multi_domain_mixed(rest):
    """Mixed operations across light, switch, sensor, cover domains."""
    tag = uuid.uuid4().hex[:8]
    ops = []

    # Light turn on
    for i in range(5):
        eid = f"light.mw_md_l_{i}_{tag}"
        await rest.set_state(eid, "off")
        ops.append(rest.call_service("light", "turn_on", {
            "entity_id": eid, "brightness": 200,
        }))

    # Switch toggle
    for i in range(5):
        eid = f"switch.mw_md_s_{i}_{tag}"
        await rest.set_state(eid, "off")
        ops.append(rest.call_service("switch", "toggle", {"entity_id": eid}))

    # Sensor writes
    for i in range(5):
        ops.append(rest.set_state(f"sensor.mw_md_n_{i}_{tag}", str(i * 10)))

    # Cover operations
    for i in range(5):
        eid = f"cover.mw_md_c_{i}_{tag}"
        await rest.set_state(eid, "closed")
        ops.append(rest.call_service("cover", "open_cover", {"entity_id": eid}))

    await asyncio.gather(*ops)

    # Verify results
    assert (await rest.get_state(f"light.mw_md_l_0_{tag}"))["state"] == "on"
    assert (await rest.get_state(f"switch.mw_md_s_0_{tag}"))["state"] == "on"
    assert (await rest.get_state(f"sensor.mw_md_n_2_{tag}"))["state"] == "20"
    assert (await rest.get_state(f"cover.mw_md_c_0_{tag}"))["state"] == "open"


# ── Health Responsive During Mixed Load ────────────────────

async def test_health_during_mixed_load(rest):
    """Health endpoint responds during concurrent mixed operations."""
    tag = uuid.uuid4().hex[:8]

    async def background_load():
        for i in range(20):
            await rest.set_state(f"sensor.mw_hl_{i}_{tag}", str(i))
            await rest.call_service("light", "turn_on", {
                "entity_id": f"light.mw_hl_{i}_{tag}",
            })

    load_task = asyncio.create_task(background_load())

    resp = await rest.client.get(f"{rest.base_url}/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    await load_task


# ── Template Renders Under Load ────────────────────────────

async def test_template_accuracy_under_load(rest):
    """Templates return correct values while other operations run."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mw_tpl_{tag}"
    await rest.set_state(eid, "42")

    async def background_writes():
        for i in range(20):
            await rest.set_state(f"sensor.mw_bg_{i}_{tag}", str(i))

    write_task = asyncio.create_task(background_writes())

    # Render template multiple times
    for _ in range(5):
        resp = await rest.client.post(
            f"{rest.base_url}/api/template",
            json={"template": f"{{{{ states('{eid}') | int * 2 }}}}"},
            headers=rest._headers(),
        )
        assert resp.status_code == 200
        assert "84" in resp.text

    await write_task


# ── Concurrent Service + State Read Consistency ────────────

async def test_service_read_consistency(rest):
    """State read after service call returns the new state."""
    tag = uuid.uuid4().hex[:8]
    tasks = []

    for i in range(10):
        eid = f"light.mw_rc_{i}_{tag}"
        await rest.set_state(eid, "off")

    async def turn_on_and_verify(eid):
        await rest.call_service("light", "turn_on", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "on"

    verify_tasks = [
        turn_on_and_verify(f"light.mw_rc_{i}_{tag}")
        for i in range(10)
    ]
    await asyncio.gather(*verify_tasks)


# ── Mixed Read Throughput ──────────────────────────────────

async def test_mixed_read_throughput(rest):
    """Mixed reads (get_state + search + health) maintain throughput."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.mw_rt_{tag}"
    await rest.set_state(eid, "42")

    t0 = time.monotonic()
    tasks = []
    for _ in range(30):
        tasks.append(rest.get_state(eid))
    for _ in range(10):
        tasks.append(rest.client.get(
            f"{rest.base_url}/api/states/search?q={tag}",
            headers=rest._headers(),
        ))
    for _ in range(10):
        tasks.append(rest.client.get(f"{rest.base_url}/api/health"))

    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - t0
    throughput = 50 / elapsed

    # All should succeed
    assert all(r is not None for r in results[:30])
    assert throughput > 50, f"Mixed throughput {throughput:.0f} ops/s below 50"
