"""
CTS -- REST Webhook & Event Fire Depth Tests

Tests POST /api/webhook/<id> receiver and POST /api/events/<type>
event fire endpoint.
"""

import uuid
import pytest

pytestmark = pytest.mark.asyncio


# ── Webhook Receiver ────────────────────────────────────

async def test_webhook_returns_200(rest):
    """POST /api/webhook/<id> returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_{tag}",
        headers=rest._headers(),
        json={"data": "test"},
    )
    assert resp.status_code == 200


async def test_webhook_accepts_empty_body(rest):
    """POST /api/webhook/<id> accepts empty body."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/webhook/hook_empty_{tag}",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 200


async def test_webhook_different_ids(rest):
    """Different webhook IDs all accepted."""
    for i in range(3):
        tag = uuid.uuid4().hex[:8]
        resp = await rest.client.post(
            f"{rest.base_url}/api/webhook/wh_{i}_{tag}",
            headers=rest._headers(),
            json={"idx": i},
        )
        assert resp.status_code == 200


# ── Event Fire ──────────────────────────────────────────

async def test_fire_event_returns_200(rest):
    """POST /api/events/<type> returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/test_event_{tag}",
        headers=rest._headers(),
        json={},
    )
    assert resp.status_code == 200


async def test_fire_event_with_data(rest):
    """POST /api/events/<type> with data returns 200."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/custom_event_{tag}",
        headers=rest._headers(),
        json={"key": "value", "num": 42},
    )
    assert resp.status_code == 200


async def test_fire_event_returns_json(rest):
    """POST /api/events/<type> returns JSON response."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/json_event_{tag}",
        headers=rest._headers(),
        json={},
    )
    data = resp.json()
    assert isinstance(data, dict)


async def test_fire_event_message_field(rest):
    """Event fire response has message field."""
    tag = uuid.uuid4().hex[:8]
    resp = await rest.client.post(
        f"{rest.base_url}/api/events/msg_event_{tag}",
        headers=rest._headers(),
        json={},
    )
    data = resp.json()
    assert "message" in data
