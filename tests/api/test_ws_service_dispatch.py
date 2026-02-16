"""
CTS -- WebSocket Service Call Dispatch Tests

Tests WebSocket service call paths: target entity patterns,
entity arrays, missing entities, cross-domain dispatch, service
response format, persistent notifications, fire_event, get_services,
and unsubscribe_events.

Consolidated from:
  - test_ws_service_dispatch.py (original target)
  - test_ws_special_dispatch.py
  - test_ws_fire_event_services.py
  - test_ws_service_response_format.py
  - test_ws_notifications_events.py
  - test_ws_advanced.py (service/fire_event/notification tests only)
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Basic call_service Dispatch ──────────────────────────────


async def test_ws_call_service_with_target(ws, rest):
    """WS call_service with target.entity_id works."""
    await rest.set_state("light.ws_svc_t1", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": "light.ws_svc_t1"},
    )
    assert resp["success"] is True


async def test_ws_call_service_with_service_data(ws, rest):
    """WS call_service with service_data.entity_id works."""
    await rest.set_state("switch.ws_svc_d1", "off")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": "switch.ws_svc_d1"},
    )
    assert resp["success"] is True
    state = await rest.get_state("switch.ws_svc_d1")
    assert state["state"] == "on"


async def test_ws_call_service_entity_array(ws, rest):
    """WS call_service with array of entity_ids."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"light.ws_arr1_{tag}"
    eid2 = f"light.ws_arr2_{tag}"
    await rest.set_state(eid1, "off")
    await rest.set_state(eid2, "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid1, eid2]},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid1))["state"] == "on"
    assert (await rest.get_state(eid2))["state"] == "on"


async def test_ws_call_service_with_data(ws, rest):
    """WS call_service passes data to service handler."""
    await rest.set_state("light.ws_svc_data", "off")
    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        target={"entity_id": "light.ws_svc_data"},
        service_data={"brightness": 128},
    )
    assert resp["success"] is True
    state = await rest.get_state("light.ws_svc_data")
    assert state["state"] == "on"
    assert state["attributes"].get("brightness") == 128


async def test_ws_call_service_toggle(ws, rest):
    """WS call_service toggle switches state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_sw_{tag}"
    await rest.set_state(eid, "on")
    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "off"


async def test_ws_call_service_climate(ws, rest):
    """WS call_service for climate domain works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"climate.ws_clim_{tag}"
    await rest.set_state(eid, "heat")
    resp = await ws.send_command(
        "call_service",
        domain="climate",
        service="set_temperature",
        service_data={"entity_id": eid, "temperature": 72},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"]["temperature"] == 72


async def test_ws_call_service_lock(ws, rest):
    """WS call_service for lock domain works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ws_lk_{tag}"
    await rest.set_state(eid, "unlocked")
    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="lock",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "locked"


async def test_ws_call_service_scene(ws, rest):
    """WS call_service activating a scene works."""
    resp = await ws.send_command(
        "call_service",
        domain="scene",
        service="turn_on",
        target={"entity_id": "scene.evening"},
    )
    assert resp["success"] is True


async def test_ws_call_service_light_with_brightness(ws, rest):
    """WS call_service light.turn_on with brightness sets attribute."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_lt_{tag}"
    await rest.set_state(eid, "off")
    resp = await ws.send_command("call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid, "brightness": 200},
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["state"] == "on"
    assert state["attributes"]["brightness"] == 200


async def test_ws_call_service_target_entity_array(ws, rest):
    """WS call_service with target.entity_id as array."""
    tag = uuid.uuid4().hex[:8]
    eid1 = f"switch.ws_tga1_{tag}"
    eid2 = f"switch.ws_tga2_{tag}"
    await rest.set_state(eid1, "on")
    await rest.set_state(eid2, "on")
    resp = await ws.send_command("call_service",
        domain="switch",
        service="turn_off",
        service_data={},
        target={"entity_id": [eid1, eid2]},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid1))["state"] == "off"
    assert (await rest.get_state(eid2))["state"] == "off"


@pytest.mark.parametrize("domain,service,entity_prefix,initial_state,service_data_extra,expected_attr,expected_attr_val", [
    ("cover", "set_cover_position", "cover.ws_cvr", "closed", {"position": 50}, "current_position", 50),
    ("fan", "set_percentage", "fan.ws_fn", "on", {"percentage": 75}, "percentage", 75),
    ("media_player", "volume_set", "media_player.ws_mp", "playing", {"volume_level": 0.6}, "volume_level", 0.6),
], ids=["cover-position", "fan-percentage", "media-player-volume"])
async def test_ws_call_service_attribute_domains(ws, rest, domain, service, entity_prefix, initial_state, service_data_extra, expected_attr, expected_attr_val):
    """WS call_service for various domains sets expected attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"{entity_prefix}_{tag}"
    await rest.set_state(eid, initial_state)
    svc_data = {"entity_id": eid, **service_data_extra}
    resp = await ws.send_command("call_service",
        domain=domain,
        service=service,
        service_data=svc_data,
    )
    assert resp["success"] is True
    state = await rest.get_state(eid)
    assert state["attributes"][expected_attr] == expected_attr_val


async def test_ws_call_counter_increment(ws, rest):
    """WS call_service counter.increment increases value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"counter.ws_ctr_{tag}"
    await rest.set_state(eid, "10")
    resp = await ws.send_command("call_service",
        domain="counter",
        service="increment",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert (await rest.get_state(eid))["state"] == "11"


# ── Automation Dispatch ──────────────────────────────────────


async def test_ws_automation_trigger(ws, rest):
    """WS call_service automation.trigger fires automation."""
    resp = await ws.send_command(
        "call_service",
        domain="automation",
        service="trigger",
        service_data={"entity_id": "automation.smoke_co_emergency"},
    )
    assert resp.get("success", False) is True


async def test_ws_automation_turn_off(ws, rest):
    """WS call_service automation.turn_off disables automation."""
    eid = "automation.morning_wakeup"

    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_off",
        service_data={"entity_id": eid},
    )

    state = await rest.get_state(eid)
    assert state["state"] == "off"

    # Re-enable
    await ws.send_command(
        "call_service",
        domain="automation",
        service="turn_on",
        service_data={"entity_id": eid},
    )


async def test_ws_automation_toggle(ws, rest):
    """WS call_service automation.toggle flips enabled state."""
    eid = "automation.morning_wakeup"
    state_before = await rest.get_state(eid)
    was_on = state_before["state"] == "on"

    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )

    state_after = await rest.get_state(eid)
    if was_on:
        assert state_after["state"] == "off"
    else:
        assert state_after["state"] == "on"

    # Toggle back
    await ws.send_command(
        "call_service",
        domain="automation",
        service="toggle",
        service_data={"entity_id": eid},
    )


# ── fire_event Command ──────────────────────────────────────


async def test_ws_fire_event(ws):
    """WS fire_event command works."""
    resp = await ws.send_command(
        "fire_event",
        event_type="test_ws_fire",
        event_data={"key": "value"},
    )
    assert resp["success"] is True


@pytest.mark.parametrize("event_type", [
    pytest.param(None, id="no-event-type"),
    pytest.param("", id="empty-event-type"),
])
async def test_fire_event_edge_cases(ws, event_type):
    """fire_event with missing or empty event_type still returns success."""
    kwargs = {}
    if event_type is not None:
        kwargs["event_type"] = event_type
    resp = await ws.send_command("fire_event", **kwargs)
    assert resp["success"] is True


async def test_fire_event_multiple_sequential(ws):
    """Multiple fire_event calls all return success."""
    for i in range(5):
        resp = await ws.send_command(
            "fire_event",
            event_type=f"batch_event_{i}",
        )
        assert resp["success"] is True


async def test_fire_event_custom_type(ws):
    """WS fire_event with custom event type succeeds."""
    resp = await ws.send_command(
        "fire_event",
        event_type="custom_integration_event",
        event_data={"source": "test"},
    )
    assert resp.get("success", False) is True


async def test_fire_event_no_data(ws):
    """WS fire_event without event_data succeeds."""
    resp = await ws.send_command(
        "fire_event",
        event_type="minimal_event",
    )
    assert resp.get("success", False) is True


# ── get_services Command ─────────────────────────────────────


async def test_ws_get_services(ws):
    """WS get_services returns service registry."""
    resp = await ws.send_command("get_services")
    assert resp["success"] is True
    assert "result" in resp
    result = resp["result"]
    assert isinstance(result, list)
    domains = [s["domain"] for s in result]
    assert "light" in domains
    assert "switch" in domains


@pytest.mark.parametrize("domain", ["light", "switch", "climate"],
                         ids=["light", "switch", "climate"])
async def test_get_services_has_domain(ws, domain):
    """get_services includes expected domains."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert domain in domains


async def test_get_services_domain_entry_format(ws):
    """Each domain entry has 'domain' and 'services' keys."""
    resp = await ws.send_command("get_services")
    for entry in resp["result"]:
        assert "domain" in entry, f"Missing 'domain' in entry: {entry}"
        assert "services" in entry, f"Missing 'services' in entry: {entry}"
        assert isinstance(entry["services"], dict)


async def test_get_services_light_has_turn_on(ws):
    """Light domain includes turn_on service."""
    resp = await ws.send_command("get_services")
    light = next(e for e in resp["result"] if e["domain"] == "light")
    assert "turn_on" in light["services"]


async def test_get_services_service_has_description(ws):
    """Service entries have description field."""
    resp = await ws.send_command("get_services")
    light = next(e for e in resp["result"] if e["domain"] == "light")
    turn_on = light["services"]["turn_on"]
    assert "description" in turn_on


async def test_get_services_matches_rest(ws, rest):
    """WS get_services matches REST /api/services output."""
    ws_resp = await ws.send_command("get_services")
    rest_resp = await rest.client.get(
        f"{rest.base_url}/api/services",
        headers=rest._headers(),
    )
    assert rest_resp.status_code == 200
    rest_services = rest_resp.json()

    ws_domains = sorted(e["domain"] for e in ws_resp["result"])
    rest_domains = sorted(e["domain"] for e in rest_services)
    assert ws_domains == rest_domains


async def test_get_services_sorted_by_domain(ws):
    """get_services result is sorted alphabetically by domain."""
    resp = await ws.send_command("get_services")
    domains = [e["domain"] for e in resp["result"]]
    assert domains == sorted(domains)


# ── get_config ───────────────────────────────────────────────


async def test_ws_get_config(ws):
    """WS get_config returns config object."""
    resp = await ws.send_command("get_config")
    assert resp["success"] is True
    result = resp["result"]
    assert "latitude" in result
    assert "longitude" in result
    assert "state" in result


# ── Service Response Format ──────────────────────────────────


async def test_call_service_returns_result(ws, rest):
    """WS call_service response has 'result' field."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_resp_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    assert resp["success"] is True
    assert "result" in resp


async def test_call_service_result_is_list(ws, rest):
    """call_service result is a list of changed states."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_list_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    result = resp["result"]
    assert isinstance(result, list)
    assert len(result) >= 1


async def test_changed_state_has_entity_id(ws, rest):
    """Changed state entries include entity_id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_eid_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["entity_id"] == eid


async def test_changed_state_has_state_field(ws, rest):
    """Changed state entries include 'state' string."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_state_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "on"


async def test_changed_state_has_attributes(ws, rest):
    """Changed state entries include 'attributes' dict."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_attrs_{tag}"
    await rest.set_state(eid, "off", {"friendly_name": f"WS Test {tag}"})

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "attributes" in entry
    assert isinstance(entry["attributes"], dict)


async def test_changed_state_has_timestamps(ws, rest):
    """Changed state entries include last_changed and last_updated."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_time_{tag}"
    await rest.set_state(eid, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "last_changed" in entry
    assert "last_updated" in entry


async def test_changed_state_has_context(ws, rest):
    """Changed state entries include context with id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"lock.ws_ctx_{tag}"
    await rest.set_state(eid, "locked")

    resp = await ws.send_command(
        "call_service",
        domain="lock",
        service="unlock",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert "context" in entry
    assert "id" in entry["context"]


async def test_multi_entity_service_response(ws, rest):
    """call_service with multiple entities returns all changed states."""
    tag = uuid.uuid4().hex[:8]
    eid_a = f"light.ws_multi_a_{tag}"
    eid_b = f"light.ws_multi_b_{tag}"
    await rest.set_state(eid_a, "off")
    await rest.set_state(eid_b, "off")

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_on",
        service_data={"entity_id": [eid_a, eid_b]},
    )
    assert resp["success"] is True
    result = resp["result"]
    assert len(result) == 2
    entity_ids = [e["entity_id"] for e in result]
    assert eid_a in entity_ids
    assert eid_b in entity_ids


async def test_toggle_response_reflects_new_state(ws, rest):
    """Toggle response shows the new (toggled) state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"switch.ws_toggle_{tag}"
    await rest.set_state(eid, "on")

    resp = await ws.send_command(
        "call_service",
        domain="switch",
        service="toggle",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "off"


async def test_service_preserves_attributes_in_response(ws, rest):
    """Service call response preserves existing attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.ws_pres_{tag}"
    await rest.set_state(eid, "on", {"brightness": 100, "friendly_name": f"Lamp {tag}"})

    resp = await ws.send_command(
        "call_service",
        domain="light",
        service="turn_off",
        service_data={"entity_id": eid},
    )
    entry = resp["result"][0]
    assert entry["state"] == "off"
    assert entry["attributes"].get("brightness") == 100
    assert entry["attributes"].get("friendly_name") == f"Lamp {tag}"


# ── Persistent Notifications ─────────────────────────────────


async def test_create_notification(ws):
    """WS call_service persistent_notification.create succeeds."""
    tag = uuid.uuid4().hex[:8]
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": f"test_{tag}",
            "title": "Test Title",
            "message": "Test body message",
        },
    )
    assert resp.get("success", False) is True


async def test_get_notifications(ws):
    """WS get_notifications returns list."""
    resp = await ws.send_command("get_notifications")
    assert resp.get("success", False) is True
    result = resp.get("result", [])
    assert isinstance(result, list)


async def test_create_and_list_notification(ws):
    """Created notification appears in get_notifications."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"list_{tag}"

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "Listed",
            "message": "Should appear in list",
        },
    )

    # List
    resp = await ws.send_command("get_notifications")
    result = resp.get("result", [])
    ids = [n["notification_id"] for n in result]
    assert notif_id in ids


async def test_notification_fields(ws):
    """Created notification has title, message, created_at."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"fields_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "My Title",
            "message": "My Message",
        },
    )

    resp = await ws.send_command("get_notifications")
    result = resp.get("result", [])
    found = [n for n in result if n["notification_id"] == notif_id]
    assert len(found) == 1
    assert found[0]["title"] == "My Title"
    assert found[0]["message"] == "My Message"
    assert "created_at" in found[0]


async def test_dismiss_notification(ws):
    """WS persistent_notification/dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"dismiss_{tag}"

    # Create
    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "To Dismiss",
            "message": "Going away",
        },
    )

    # Dismiss
    resp = await ws.send_command(
        "persistent_notification/dismiss",
        notification_id=notif_id,
    )
    assert resp.get("success", False) is True

    # Verify gone from list
    list_resp = await ws.send_command("get_notifications")
    ids = [n["notification_id"] for n in list_resp.get("result", [])]
    assert notif_id not in ids


async def test_dismiss_all_notifications(ws):
    """WS call_service persistent_notification.dismiss_all clears all."""
    tag = uuid.uuid4().hex[:8]

    # Create two notifications
    for i in range(2):
        await ws.send_command(
            "call_service",
            domain="persistent_notification",
            service="create",
            service_data={
                "notification_id": f"all_{tag}_{i}",
                "title": f"Bulk {i}",
                "message": "Dismiss all test",
            },
        )

    # Dismiss all
    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss_all",
        service_data={},
    )
    assert resp.get("success", False) is True

    # Verify all dismissed
    list_resp = await ws.send_command("get_notifications")
    result = list_resp.get("result", [])
    remaining = [n for n in result if n["notification_id"].startswith(f"all_{tag}")]
    assert len(remaining) == 0


async def test_overwrite_notification(ws):
    """Creating notification with same ID overwrites it."""
    tag = uuid.uuid4().hex[:8]
    notif_id = f"overwrite_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "V1",
            "message": "First",
        },
    )

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": notif_id,
            "title": "V2",
            "message": "Second",
        },
    )

    resp = await ws.send_command("get_notifications")
    found = [n for n in resp.get("result", []) if n["notification_id"] == notif_id]
    assert len(found) == 1
    assert found[0]["title"] == "V2"
    assert found[0]["message"] == "Second"


async def test_ws_notification_dismiss_via_call_service(ws):
    """WS call_service persistent_notification.dismiss removes notification."""
    tag = uuid.uuid4().hex[:8]
    nid = f"wsdismiss_{tag}"

    await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="create",
        service_data={
            "notification_id": nid,
            "title": "Dismiss",
            "message": "Will be dismissed",
        },
    )

    resp = await ws.send_command(
        "call_service",
        domain="persistent_notification",
        service="dismiss",
        service_data={"notification_id": nid},
    )
    assert resp.get("success", False) is True


# ── Unsubscribe Events ──────────────────────────────────────


async def test_ws_unsubscribe_events(ws, rest):
    """unsubscribe_events stops event delivery."""
    sub_id = await ws.subscribe_events("state_changed")
    # Unsubscribe
    result = await ws.send_command(
        "unsubscribe_events",
        subscription=sub_id,
    )
    assert result["success"] is True
    # Change state -- should NOT receive event
    await rest.set_state("sensor.ws_unsub_test", "changed")
    try:
        event = await ws.recv_event(timeout=0.5)
        # If we get here, verify it's NOT from our subscription
        assert event["id"] != sub_id
    except asyncio.TimeoutError:
        pass  # Expected -- no event for unsubscribed
