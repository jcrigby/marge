"""
CTS -- Entity Lifecycle Depth Tests

Tests the complete entity lifecycle: create → read → update → service
call → event → history → delete → verify gone → recreate. Also tests
entity_count tracking and context uniqueness across operations.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Full Lifecycle ─────────────────────────────────────────

async def test_entity_full_lifecycle(rest):
    """Create → update → service → delete → recreate lifecycle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lc_{tag}"

    # Create
    await rest.set_state(eid, "off", {"friendly_name": f"Lifecycle {tag}"})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["friendly_name"] == f"Lifecycle {tag}"

    # Update state
    await rest.set_state(eid, "on", {"brightness": 100})
    state = await rest.get_state(eid)
    assert state["state"] == "on"

    # Service call
    await rest.call_service("light", "turn_on", {
        "entity_id": eid, "brightness": 255,
    })
    state = await rest.get_state(eid)
    assert state["attributes"]["brightness"] == 255

    # Delete
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify gone
    assert await rest.get_state(eid) is None

    # Recreate with different state
    await rest.set_state(eid, "off", {"brightness": 50})
    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["brightness"] == 50


# ── Entity Count Tracking ──────────────────────────────────

async def test_entity_count_increases(rest):
    """Health entity_count increases after creating entities."""
    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    base = h1["entity_count"]

    tag = uuid.uuid4().hex[:8]
    for i in range(5):
        await rest.set_state(f"sensor.ec_{i}_{tag}", str(i))

    h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    assert h2["entity_count"] >= base + 5


async def test_entity_count_decreases_on_delete(rest):
    """Health entity_count decreases when entity is deleted."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ec_del_{tag}"
    await rest.set_state(eid, "42")

    h1 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    count_before = h1["entity_count"]

    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )

    h2 = (await rest.client.get(f"{rest.base_url}/api/health")).json()
    assert h2["entity_count"] == count_before - 1


# ── Context Uniqueness ─────────────────────────────────────

async def test_context_id_unique_per_set(rest):
    """Each set_state produces a unique context.id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_uniq_{tag}"

    await rest.set_state(eid, "A")
    s1 = await rest.get_state(eid)
    await rest.set_state(eid, "B")
    s2 = await rest.get_state(eid)
    await rest.set_state(eid, "C")
    s3 = await rest.get_state(eid)

    ctx1 = s1["context"]["id"]
    ctx2 = s2["context"]["id"]
    ctx3 = s3["context"]["id"]

    assert ctx1 != ctx2
    assert ctx2 != ctx3
    assert ctx1 != ctx3


async def test_context_id_present_on_new_entity(rest):
    """New entity has context.id from first set."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.ctx_new_{tag}"
    await rest.set_state(eid, "first")
    state = await rest.get_state(eid)
    assert "context" in state
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


# ── History After Lifecycle ────────────────────────────────

async def test_history_records_changes(rest):
    """History records state changes through lifecycle."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_hist_{tag}"
    await rest.set_state(eid, "10")
    await rest.set_state(eid, "20")
    await rest.set_state(eid, "30")
    await asyncio.sleep(0.3)

    resp = await rest.client.get(
        f"{rest.base_url}/api/history/period/{eid}",
        headers=rest._headers(),
    )
    entries = resp.json()
    states = [e["state"] for e in entries]
    assert "10" in states
    assert "20" in states
    assert "30" in states


async def test_deleted_entity_returns_404(rest):
    """Deleted entity returns 404 on subsequent GET."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_del_{tag}"
    await rest.set_state(eid, "42")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    resp = await rest.client.get(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 404


# ── Service on Deleted Entity ──────────────────────────────

async def test_service_recreates_deleted_entity(rest):
    """Service call on deleted entity recreates it."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.lc_svc_del_{tag}"
    await rest.set_state(eid, "on")
    await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert await rest.get_state(eid) is None

    await rest.call_service("light", "turn_on", {"entity_id": eid})
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "on"


# ── Multiple Entities Same Domain ──────────────────────────

async def test_many_entities_all_independent(rest):
    """Creating many entities in same domain, all independently readable."""
    tag = uuid.uuid4().hex[:8]
    count = 20
    for i in range(count):
        await rest.set_state(f"sensor.lc_ind_{i}_{tag}", str(i * 10))

    for i in range(count):
        state = await rest.get_state(f"sensor.lc_ind_{i}_{tag}")
        assert state["state"] == str(i * 10)


# ── Entity Update Preserves Fields ────────────────────────

async def test_update_preserves_entity_id(rest):
    """Updating entity state doesn't change entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.lc_pid_{tag}"
    await rest.set_state(eid, "A")
    await rest.set_state(eid, "B")
    state = await rest.get_state(eid)
    assert state["entity_id"] == eid
