"""
CTS -- REST /api/template Endpoint Tests

Tests the POST /api/template endpoint for rendering Jinja2 templates
with state machine access, filter chains, error handling, and edge cases.
"""

import asyncio
import uuid
import pytest

pytestmark = pytest.mark.asyncio

BASE = "http://localhost:8124"
HEADERS = {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


async def test_template_simple_expression(rest):
    """POST /api/template renders simple arithmetic."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 1 + 2 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "3" in resp.text


async def test_template_string_literal(rest):
    """POST /api/template renders string literal."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "Hello {{ 'World' }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "Hello World" in resp.text


async def test_template_states_function(rest):
    """POST /api/template accesses state machine via states()."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_rest_{tag}"
    await rest.set_state(eid, "99.5")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ states('{eid}') }}}}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "99.5" in resp.text


async def test_template_is_state_function(rest):
    """POST /api/template is_state returns true/false."""
    tag = uuid.uuid4().hex[:8]
    eid = f"light.tpl_rest_is_{tag}"
    await rest.set_state(eid, "on")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ is_state('{eid}', 'on') }}}}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip().lower() == "true"


async def test_template_filter_chain(rest):
    """POST /api/template supports filter chains."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_rest_chain_{tag}"
    await rest.set_state(eid, "3.14159")

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ states('{eid}') | float | round(2) }}}}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "3.14" in resp.text


async def test_template_conditional(rest):
    """POST /api/template handles if/else conditionals."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% if true %}yes{% else %}no{% endif %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "yes"


async def test_template_for_loop(rest):
    """POST /api/template handles for loops."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{% for i in range(3) %}{{ i }}{% endfor %}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "012" in resp.text


async def test_template_now_function(rest):
    """POST /api/template now() returns timestamp."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ now() }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "20" in resp.text  # Year prefix


async def test_template_invalid_syntax_returns_400(rest):
    """POST /api/template with invalid syntax returns 400."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ invalid syntax {{"},
        headers=rest._headers(),
    )
    assert resp.status_code == 400


async def test_template_empty_string(rest):
    """POST /api/template with empty template returns 200."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": ""},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == ""


async def test_template_plain_text(rest):
    """POST /api/template with no Jinja syntax returns text as-is."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "Hello plain text"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert resp.text.strip() == "Hello plain text"


async def test_template_state_attr_function(rest):
    """POST /api/template state_attr returns attribute value."""
    tag = uuid.uuid4().hex[:8]
    eid = f"sensor.tpl_rest_attr_{tag}"
    await rest.set_state(eid, "val", {"unit": "kWh"})

    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": f"{{{{ state_attr('{eid}', 'unit') }}}}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "kWh" in resp.text


async def test_template_multiple_expressions(rest):
    """POST /api/template renders multiple expressions in one template."""
    resp = await rest.client.post(
        f"{rest.base_url}/api/template",
        json={"template": "{{ 1 + 1 }} and {{ 2 * 3 }}"},
        headers=rest._headers(),
    )
    assert resp.status_code == 200
    assert "2 and 6" in resp.text
