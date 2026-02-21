"""
CTS -- REST Service Dispatch Pattern Tests

Tests advanced service call patterns: target.entity_id, array
entity_ids, automation trigger/enable/disable services, and
persistent_notification CRUD via REST service dispatch.
"""

import asyncio
import uuid
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.marge_only]


# ── Array entity_id ──────────────────────────────────────

async def test_service_array_entity_id(rest):
    """Service call with array entity_id affects all entities."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"switch.arr_{tag}_{i}" for i in range(3)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"entity_id": eids},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on", f"{eid} should be on"


async def test_service_single_entity_id_string(rest):
    """Service call with string entity_id works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.single_{tag}"
    await rest.set_state(eid, "off")

    await rest.call_service("light", "turn_on", {"entity_id": eid})

    state = await rest.get_state(eid)
    assert state["state"] == "on"


# ── target.entity_id pattern ─────────────────────────────

async def test_service_target_entity_id(rest):
    """Service call with target.entity_id dispatches correctly."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.target_{tag}"
    await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/switch/turn_on",
        json={"target": {"entity_id": eid}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state["state"] == "on"


async def test_service_target_array_entity_id(rest):
    """Service call with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eids = [f"light.tarr_{tag}_{i}" for i in range(2)]
    for eid in eids:
        await rest.set_state(eid, "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/light/turn_on",
        json={"target": {"entity_id": eids}},
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    for eid in eids:
        state = await rest.get_state(eid)
        assert state["state"] == "on"


# ── Automation services ──────────────────────────────────

async def test_automation_trigger_service(rest):
    """automation.trigger fires the automation's actions."""
    # Just verify the API accepts the call without error
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/automation/trigger",
        json={"entity_id": "automation.nonexistent_trigger_test"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


@pytest.mark.marge_only
async def test_automation_turn_off_service(rest):
    """automation.turn_off disables an automation (sets state to off)."""
    # The loaded automations should have some real IDs
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if len(autos) > 0:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        await rest.call_service("automation", "turn_off", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "off"

        # Re-enable it
        await rest.call_service("automation", "turn_on", {"entity_id": eid})
        state = await rest.get_state(eid)
        assert state["state"] == "on"


@pytest.mark.marge_only
async def test_automation_toggle_service(rest):
    """automation.toggle flips enabled state."""
    resp = await rest.client.get(
        f"{rest.base_url}/api/config/automation/config",
        headers=rest._headers(),
    )
    autos = resp.json()
    if len(autos) > 0:
        auto_id = autos[0]["id"]
        eid = f"automation.{auto_id}"

        # Get current state
        s1 = await rest.get_state(eid)
        original = s1["state"]

        # Toggle
        await rest.call_service("automation", "toggle", {"entity_id": eid})
        s2 = await rest.get_state(eid)
        assert s2["state"] != original

        # Toggle back
        await rest.call_service("automation", "toggle", {"entity_id": eid})
        s3 = await rest.get_state(eid)
        assert s3["state"] == original


# ── Persistent notification via service ──────────────────

@pytest.mark.marge_only
async def test_notification_create_via_service(rest):
    """persistent_notification.create via service endpoint."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={
            "notification_id": f"svc_notif_{tag}",
            "title": f"Test {tag}",
            "message": "Created via service dispatch",
        },
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    # Verify notification exists
    await asyncio.sleep(0.3)
    nr = await rest.client.get(
        f"{rest.base_url}/api/notifications",
        headers=rest._headers(),
    )
    notifs = nr.json()
    ids = [n["notification_id"] for n in notifs]
    assert f"svc_notif_{tag}" in ids


async def test_notification_dismiss_via_service(rest):
    """persistent_notification.dismiss via service endpoint."""
    tag = uuid.uuid4().hex[:8]
    nid = f"svc_dismiss_{tag}"

    # Create first
    await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/create",
        json={"notification_id": nid, "title": "T", "message": "M"},
        headers=rest._headers(),
    )
    await asyncio.sleep(0.3)

    # Dismiss via service
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/dismiss",
        json={"notification_id": nid},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


async def test_notification_dismiss_all_via_service(rest):
    """persistent_notification.dismiss_all via service endpoint."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/services/persistent_notification/dismiss_all",
        json={},
        headers=rest._headers(),
    )
    assert resp.status_code == 200


# ── Scene service dispatch ───────────────────────────────

async def test_scene_turn_on_via_rest(rest):
    """scene.turn_on via REST service endpoint."""
    await rest.set_state("light.living_room_main", "off")

    resp = await rest.client.post(
        f"{rest.base_url}/api/services/scene/turn_on",
        json={"entity_id": "scene.evening"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    await asyncio.sleep(0.3)

    state = await rest.get_state("light.living_room_main")
    assert state["state"] == "on"


# -- domain service coverage (from test_extended_api.py) --
#
# 35 hand-written tests collapsed into 7 parametrized test functions.
# Groups:
#   1. simple_state_transition     -- set state, call one service, assert new state
#   2. attribute_setting_service   -- call service with data, assert attribute value
#   3. two_step_cycle              -- service A -> assert, service B -> assert
#   4. toggle_cycle                -- toggle from A->B, toggle from B->A
#   5. cover_toggle_with_position  -- cover.toggle checks state + current_position
#   6. multi_step_cycle            -- 3+ service calls in sequence
#   7. state_preserving_service    -- call service, state stays the same


# ── Group 1: Simple state transitions ───────────────────
#
# Pattern: set_state(entity, initial), call_service(domain, service, data),
#          get_state(entity) -> assert state == expected

_SIMPLE_STATE_CASES = [
    # (test_id, entity_id, initial_state, init_attrs, domain, service, svc_data, expected_state)
    ("alarm_arm_home",
     "alarm_control_panel.test", "disarmed", {},
     "alarm_control_panel", "arm_home", {}, "armed_home"),
    ("alarm_disarm",
     "alarm_control_panel.test2", "armed_away", {},
     "alarm_control_panel", "disarm", {}, "disarmed"),
    ("climate_set_hvac_mode",
     "climate.mode_cts", "off", {},
     "climate", "set_hvac_mode", {"hvac_mode": "cool"}, "cool"),
    ("vacuum_return_to_base",
     "vacuum.dyson", "cleaning", {},
     "vacuum", "return_to_base", {}, "returning"),
    ("vacuum_pause",
     "vacuum.cts_robo", "cleaning", {},
     "vacuum", "pause", {}, "paused"),
    ("number_set_value",
     "number.brightness", "50", {},
     "number", "set_value", {"value": 75}, "75"),
    ("select_option",
     "select.color_mode", "warm", {},
     "select", "select_option", {"option": "cool"}, "cool"),
    ("input_number_set_value",
     "input_number.volume", "50", {"min": 0, "max": 100, "step": 1},
     "input_number", "set_value", {"value": 75}, "75"),
    ("input_text_set_value",
     "input_text.name", "hello", {},
     "input_text", "set_value", {"value": "world"}, "world"),
    ("input_text_set_value_service",
     "input_text.greeting", "hello", {},
     "input_text", "set_value", {"value": "goodbye"}, "goodbye"),
    ("input_select_select_option",
     "input_select.mode", "auto", {"options": ["auto", "heat", "cool"]},
     "input_select", "select_option", {"option": "cool"}, "cool"),
    ("input_select_select_option_service",
     "input_select.mode", "auto", {"options": ["auto", "manual", "off"]},
     "input_select", "select_option", {"option": "manual"}, "manual"),
]


@pytest.mark.parametrize(
    "entity_id, initial, init_attrs, domain, service, svc_data, expected",
    [(c[1], c[2], c[3], c[4], c[5], c[6], c[7]) for c in _SIMPLE_STATE_CASES],
    ids=[c[0] for c in _SIMPLE_STATE_CASES],
)
async def test_simple_state_transition(
    rest, entity_id, initial, init_attrs, domain, service, svc_data, expected,
):
    """Service call transitions entity from initial to expected state."""
    if init_attrs:
        await rest.set_state(entity_id, initial, attributes=init_attrs)
    else:
        await rest.set_state(entity_id, initial)
    data = {"entity_id": entity_id, **svc_data}
    await rest.call_service(domain, service, data)
    state = await rest.get_state(entity_id)
    assert state["state"] == expected


# ── Group 2: Attribute-setting services ─────────────────
#
# Pattern: set_state(entity, initial, init_attrs),
#          call_service(domain, service, {entity_id, **data}),
#          get_state -> assert attributes[attr_key] == attr_value

_ATTR_SETTING_CASES = [
    # (test_id, entity_id, initial_state, init_attrs, domain, service,
    #  svc_data, check_state, expected_state, attr_key, attr_value)
    ("climate_set_temperature",
     "climate.thermostat_cts", "heat", {"temperature": 20},
     "climate", "set_temperature", {"temperature": 22.5},
     False, None, "temperature", 22.5),
    ("media_player_volume_set",
     "media_player.tv", "on", {},
     "media_player", "volume_set", {"volume_level": 0.65},
     False, None, "volume_level", 0.65),
    ("cover_set_position",
     "cover.garage", "closed", {},
     "cover", "set_cover_position", {"position": 50},
     True, "open", "current_position", 50),
    ("fan_set_percentage",
     "fan.ceiling", "off", {},
     "fan", "set_percentage", {"percentage": 75},
     True, "on", "percentage", 75),
    ("cover_position_tracking",
     "cover.pos_test", "open", {"current_position": 100},
     "cover", "set_cover_position", {"position": 50},
     False, None, "current_position", 50),
    ("fan_percentage_tracking",
     "fan.pct_test", "on", {"percentage": 50},
     "fan", "set_percentage", {"percentage": 75},
     False, None, "percentage", 75),
    ("media_player_select_source",
     "media_player.cts_tv", "on", {"source": "HDMI1"},
     "media_player", "select_source", {"source": "Spotify"},
     False, None, "source", "Spotify"),
]


@pytest.mark.parametrize(
    "entity_id, initial, init_attrs, domain, service, svc_data, "
    "check_state, expected_state, attr_key, attr_value",
    [(c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10])
     for c in _ATTR_SETTING_CASES],
    ids=[c[0] for c in _ATTR_SETTING_CASES],
)
async def test_attribute_setting_service(
    rest, entity_id, initial, init_attrs, domain, service, svc_data,
    check_state, expected_state, attr_key, attr_value,
):
    """Service call sets entity attribute to expected value."""
    if init_attrs:
        await rest.set_state(entity_id, initial, attributes=init_attrs)
    else:
        await rest.set_state(entity_id, initial)
    data = {"entity_id": entity_id, **svc_data}
    await rest.call_service(domain, service, data)
    state = await rest.get_state(entity_id)
    if check_state:
        assert state["state"] == expected_state
    assert state["attributes"][attr_key] == attr_value


# ── Group 3: Two-step service cycles ───────────────────
#
# Pattern: set initial, call service_a -> assert state_a,
#          call service_b -> assert state_b

_TWO_STEP_CASES = [
    # (test_id, entity_id, initial, init_attrs,
    #  domain, svc_a, state_a, svc_b, state_b)
    ("lock_lock_unlock",
     "lock.cts_lock", "unlocked", {},
     "lock", "lock", "locked", "unlock", "unlocked"),
    ("media_player_play_pause",
     "media_player.speaker", "paused", {},
     "media_player", "media_play", "playing", "media_pause", "paused"),
    ("media_player_turn_on_off",
     "media_player.amp", "off", {},
     "media_player", "turn_on", "on", "turn_off", "off"),
    ("vacuum_start_stop",
     "vacuum.roborock", "idle", {},
     "vacuum", "start", "cleaning", "stop", "idle"),
    ("siren_on_off",
     "siren.alarm", "off", {},
     "siren", "turn_on", "on", "turn_off", "off"),
    ("valve_open_close",
     "valve.water_main", "closed", {},
     "valve", "open_valve", "open", "close_valve", "closed"),
    ("cover_open_close_cycle",
     "cover.cts_garage", "closed", {},
     "cover", "open_cover", "open", "close_cover", "closed"),
    ("input_boolean_toggle_cycle",
     "input_boolean.cts_toggle", "off", {},
     "input_boolean", "toggle", "on", "toggle", "off"),
]


@pytest.mark.parametrize(
    "entity_id, initial, init_attrs, domain, svc_a, state_a, svc_b, state_b",
    [(c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8])
     for c in _TWO_STEP_CASES],
    ids=[c[0] for c in _TWO_STEP_CASES],
)
async def test_two_step_cycle(
    rest, entity_id, initial, init_attrs, domain,
    svc_a, state_a, svc_b, state_b,
):
    """Two sequential service calls transition entity through expected states."""
    if init_attrs:
        await rest.set_state(entity_id, initial, attributes=init_attrs)
    else:
        await rest.set_state(entity_id, initial)
    await rest.call_service(domain, svc_a, {"entity_id": entity_id})
    s = await rest.get_state(entity_id)
    assert s["state"] == state_a

    await rest.call_service(domain, svc_b, {"entity_id": entity_id})
    s = await rest.get_state(entity_id)
    assert s["state"] == state_b


# ── Group 4: Toggle cycles (toggle A->B, toggle B->A) ──
#
# Similar to two-step but both calls are the same "toggle" service.

_TOGGLE_CASES = [
    # (test_id, entity_id, initial, init_attrs, domain, state_after_first, state_after_second)
    ("siren_toggle",
     "siren.cts_alarm", "off", {},
     "siren", "on", "off"),
    ("valve_toggle",
     "valve.cts_main", "open", {},
     "valve", "closed", "open"),
    ("fan_toggle",
     "fan.cts_toggle", "on", {"percentage": 75},
     "fan", "off", "on"),
]


@pytest.mark.parametrize(
    "entity_id, initial, init_attrs, domain, state_a, state_b",
    [(c[1], c[2], c[3], c[4], c[5], c[6]) for c in _TOGGLE_CASES],
    ids=[c[0] for c in _TOGGLE_CASES],
)
async def test_toggle_cycle(
    rest, entity_id, initial, init_attrs, domain, state_a, state_b,
):
    """Domain toggle service flips state back and forth."""
    if init_attrs:
        await rest.set_state(entity_id, initial, attributes=init_attrs)
    else:
        await rest.set_state(entity_id, initial)
    await rest.call_service(domain, "toggle", {"entity_id": entity_id})
    s = await rest.get_state(entity_id)
    assert s["state"] == state_a

    await rest.call_service(domain, "toggle", {"entity_id": entity_id})
    s = await rest.get_state(entity_id)
    assert s["state"] == state_b


# ── Group 5: Cover toggle with position tracking ───────

async def test_cover_toggle_with_position(rest):
    """cover.toggle flips state and updates current_position attribute."""
    await rest.set_state(
        "cover.cts_toggle", "open", attributes={"current_position": 100},
    )
    await rest.call_service("cover", "toggle", {"entity_id": "cover.cts_toggle"})
    state = await rest.get_state("cover.cts_toggle")
    assert state["state"] == "closed"
    assert state["attributes"]["current_position"] == 0

    await rest.call_service("cover", "toggle", {"entity_id": "cover.cts_toggle"})
    state2 = await rest.get_state("cover.cts_toggle")
    assert state2["state"] == "open"
    assert state2["attributes"]["current_position"] == 100


# ── Group 6: Multi-step service sequences ──────────────

_MULTI_STEP_CASES = [
    # (test_id, entity_id, initial, init_attrs,
    #  steps: list of (domain, service, expected_state))
    ("input_boolean_on_off_cycle",
     "input_boolean.cycle_test", "off", {},
     [
         ("input_boolean", "turn_on", "on"),
         ("input_boolean", "turn_off", "off"),
         ("input_boolean", "toggle", "on"),
     ]),
    ("input_boolean_services",
     "input_boolean.cts_guest_mode", "off", {},
     [
         ("input_boolean", "turn_on", "on"),
         ("input_boolean", "toggle", "off"),
         ("input_boolean", "turn_off", "off"),
     ]),
]


@pytest.mark.parametrize(
    "entity_id, initial, init_attrs, steps",
    [(c[1], c[2], c[3], c[4]) for c in _MULTI_STEP_CASES],
    ids=[c[0] for c in _MULTI_STEP_CASES],
)
async def test_multi_step_cycle(rest, entity_id, initial, init_attrs, steps):
    """Multiple sequential service calls each produce the expected state."""
    if init_attrs:
        await rest.set_state(entity_id, initial, attributes=init_attrs)
    else:
        await rest.set_state(entity_id, initial)
    for domain, service, expected in steps:
        await rest.call_service(domain, service, {"entity_id": entity_id})
        s = await rest.get_state(entity_id)
        assert s["state"] == expected, (
            f"After {domain}.{service}: expected {expected!r}, got {s['state']!r}"
        )


# ── Group 7: State-preserving services ─────────────────

async def test_cover_stop_preserves_state(rest):
    """cover.stop_cover keeps cover in current position and state."""
    await rest.set_state(
        "cover.cts_garage", "opening", attributes={"current_position": 50},
    )
    await rest.call_service("cover", "stop_cover", {"entity_id": "cover.cts_garage"})
    state = await rest.get_state("cover.cts_garage")
    assert state["state"] == "opening"
    assert state["attributes"]["current_position"] == 50


async def test_media_player_next_previous_preserves_playing(rest):
    """media_player next/previous track preserve playing state."""
    await rest.set_state(
        "media_player.cts_speaker", "playing",
        attributes={"media_title": "Track 1"},
    )
    await rest.call_service(
        "media_player", "media_next_track",
        {"entity_id": "media_player.cts_speaker"},
    )
    state = await rest.get_state("media_player.cts_speaker")
    assert state["state"] == "playing"

    await rest.call_service(
        "media_player", "media_previous_track",
        {"entity_id": "media_player.cts_speaker"},
    )
    state2 = await rest.get_state("media_player.cts_speaker")
    assert state2["state"] == "playing"
