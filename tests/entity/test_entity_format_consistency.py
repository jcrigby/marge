"""
CTS -- Entity Format Consistency Tests

Tests entity JSON response format, field presence, context behavior,
timestamp semantics, attribute type preservation, and domain variety.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio


async def test_create_entity_minimal(rest):
    """Create entity with just state, no attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtmin_{tag}"
    await rest.set_state(eid, "42")

    state = await rest.get_state(eid)
    assert state["entity_id"] == eid
    assert state["state"] == "42"
    assert "attributes" in state


async def test_create_entity_with_attributes(rest):
    """Create entity with state and attributes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtattr_{tag}"
    await rest.set_state(eid, "ok", {"unit": "count", "source": "test"})

    state = await rest.get_state(eid)
    assert state["attributes"]["unit"] == "count"
    assert state["attributes"]["source"] == "test"


async def test_delete_and_recreate(rest):
    """Delete entity then recreate with new state."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtdel_{tag}"

    await rest.set_state(eid, "original")
    resp = await rest.client.delete(
        f"{rest.base_url}/api/states/{eid}",
        headers=rest._headers(),
    )
    assert resp.status_code == 200

    state = await rest.get_state(eid)
    assert state is None

    await rest.set_state(eid, "new_value")
    state = await rest.get_state(eid)
    assert state is not None
    assert state["state"] == "new_value"


async def test_entity_has_context(rest):
    """Every entity has a context with id."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtctx_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    assert "context" in state
    assert "id" in state["context"]
    assert len(state["context"]["id"]) > 0


async def test_context_changes_on_update(rest):
    """Context ID changes on each state update."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtctxc_{tag}"

    await rest.set_state(eid, "v1")
    s1 = await rest.get_state(eid)

    await rest.set_state(eid, "v2")
    s2 = await rest.get_state(eid)

    assert s1["context"]["id"] != s2["context"]["id"]


async def test_last_changed_only_on_state_change(rest):
    """last_changed only advances when state value changes."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtlc_{tag}"

    await rest.set_state(eid, "same")
    s1 = await rest.get_state(eid)

    await rest.set_state(eid, "same", {"new": "attr"})
    s2 = await rest.get_state(eid)

    assert s1["last_changed"] == s2["last_changed"]

    await rest.set_state(eid, "different")
    s3 = await rest.get_state(eid)
    assert s3["last_changed"] != s1["last_changed"]


async def test_many_domains(rest):
    """Entities can be created across many domains."""
    tag = uuid.uuid4().hex[:8]
    domains = ["sensor", "binary_sensor", "light", "switch", "lock",
               "cover", "fan", "climate", "number", "select"]

    for domain in domains:
        await rest.set_state(f"{domain}.fmtdom_{tag}", "on")

    for domain in domains:
        state = await rest.get_state(f"{domain}.fmtdom_{tag}")
        assert state is not None, f"{domain}.fmtdom_{tag} should exist"


async def test_entity_id_preserved_exactly(rest):
    """Entity ID is returned exactly as set."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.exact_id_{tag}"
    await rest.set_state(eid, "val")

    state = await rest.get_state(eid)
    assert state["entity_id"] == eid


async def test_large_attributes(rest):
    """Entity with large attribute map works."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtlg_{tag}"
    attrs = {f"key_{i}": f"value_{i}" for i in range(50)}
    await rest.set_state(eid, "complex", attrs)

    state = await rest.get_state(eid)
    assert len(state["attributes"]) >= 50
    assert state["attributes"]["key_0"] == "value_0"
    assert state["attributes"]["key_49"] == "value_49"


async def test_numeric_attribute_types(rest):
    """Integer, float, and boolean attribute values preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmttyp_{tag}"
    await rest.set_state(eid, "ok", {
        "integer": 42,
        "float_val": 3.14,
        "boolean": True,
        "null_val": None,
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["integer"] == 42
    assert abs(state["attributes"]["float_val"] - 3.14) < 0.01
    assert state["attributes"]["boolean"] is True
    assert state["attributes"]["null_val"] is None


async def test_nested_attribute_objects(rest):
    """Nested object attributes preserved."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtnest_{tag}"
    await rest.set_state(eid, "ok", {
        "config": {"timeout": 30, "enabled": True},
        "list": [1, 2, 3],
    })

    state = await rest.get_state(eid)
    assert state["attributes"]["config"]["timeout"] == 30
    assert state["attributes"]["list"] == [1, 2, 3]


async def test_response_has_required_fields(rest):
    """POST response has entity_id, state, attributes, context, timestamps."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtfld_{tag}"

    resp = await rest.client.post(
        f"{rest.base_url}/api/states/{eid}",
        json={"state": "val", "attributes": {}},
        headers=rest._headers(),
    )
    data = resp.json()
    required = ["entity_id", "state", "attributes", "context", "last_changed", "last_updated"]
    for field in required:
        assert field in data, f"Missing field: {field}"


async def test_state_empty_string(rest):
    """Empty string state is valid."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.fmtempty_{tag}"
    await rest.set_state(eid, "")

    state = await rest.get_state(eid)
    assert state["state"] == ""
