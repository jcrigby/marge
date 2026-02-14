"""
CTS -- Fan & Cover Extended Service Tests

Tests fan (turn_on with percentage, set_direction, set_preset_mode,
set_percentage with 0 = off), and cover (toggle, set_cover_position,
stop_cover, position-based state).
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Fan Extended ───────────────────────────────────────

async def test_fan_turn_on_with_percentage(rest):
    """fan.turn_on with percentage stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fp_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fan/turn_on",
        json={"entity_id": eid, "percentage": 75},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 75


async def test_fan_turn_on_with_preset(rest):
    """fan.turn_on with preset_mode stores attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fpm_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/fan/turn_on",
        json={"entity_id": eid, "preset_mode": "silent"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["preset_mode"] == "silent"


async def test_fan_set_direction(rest):
    """fan.set_direction stores direction attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fd_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_direction",
        json={"entity_id": eid, "direction": "reverse"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["attributes"]["direction"] == "reverse"


async def test_fan_set_preset_mode(rest):
    """fan.set_preset_mode stores preset_mode attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fspm_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_preset_mode",
        json={"entity_id": eid, "preset_mode": "turbo"},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["attributes"]["preset_mode"] == "turbo"


async def test_fan_set_percentage_zero_is_off(rest):
    """fan.set_percentage with 0 sets state to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fz_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_percentage",
        json={"entity_id": eid, "percentage": 0},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"
    assert state["attributes"]["percentage"] == 0


async def test_fan_set_percentage_nonzero_is_on(rest):
    """fan.set_percentage with >0 sets state to on."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.fnz_{tag}"
    await rest.set_state(eid, "off")

    await rest.client.post(
        f"{rest.base_url}/api/services/fan/set_percentage",
        json={"entity_id": eid, "percentage": 50},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["percentage"] == 50


async def test_fan_toggle_on_to_off(rest):
    """fan.toggle from on to off."""
    tag = uuid.uuid4().hex[:8]
    eid = f"fan.ft_{tag}"
    await rest.set_state(eid, "on")

    await rest.client.post(
        f"{rest.base_url}/api/services/fan/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"


# ── Cover Extended ─────────────────────────────────────

async def test_cover_open_sets_position_100(rest):
    """cover.open_cover sets current_position to 100."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cp_{tag}"
    await rest.set_state(eid, "closed")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/cover/open_cover",
        json={"entity_id": eid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_close_sets_position_0(rest):
    """cover.close_cover sets current_position to 0."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.cc_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/close_cover",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_toggle_open_to_closed(rest):
    """cover.toggle from open to closed with position."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.ct_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0


async def test_cover_toggle_closed_to_open(rest):
    """cover.toggle from closed to open with position."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.ct2_{tag}"
    await rest.set_state(eid, "closed")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/toggle",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 100


async def test_cover_set_position_partial(rest):
    """cover.set_cover_position with partial value sets open state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.csp_{tag}"
    await rest.set_state(eid, "closed")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/set_cover_position",
        json={"entity_id": eid, "position": 50},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "open"
    assert state["attributes"]["current_position"] == 50


async def test_cover_set_position_zero_is_closed(rest):
    """cover.set_cover_position with 0 sets closed state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.csz_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/set_cover_position",
        json={"entity_id": eid, "position": 0},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "closed"


async def test_cover_stop_preserves_state(rest):
    """cover.stop_cover preserves current state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"cover.css_{tag}"
    await rest.set_state(eid, "open")

    await rest.client.post(
        f"{rest.base_url}/api/services/cover/stop_cover",
        json={"entity_id": eid},
        headers=rest._headers(),
    )

    state = await rest.get_state(eid)
    assert state["state"] == "open"
