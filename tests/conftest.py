"""
MARGE CTS — Conformance Test Suite Infrastructure

conftest.py — Shared fixtures for all tests.

Usage:
    # Run against HA:
    SUT_URL=http://localhost:8123 SUT_TOKEN=xxx pytest tests/

    # Run against Marge:
    SUT_URL=http://localhost:8124 pytest tests/

    # Run against both (generates two result sets):
    pytest tests/ --sut ha --sut marge
"""

import asyncio
import json
import os
import time
from typing import AsyncGenerator, Optional

import httpx
import paho.mqtt.client as mqtt
import pytest
import pytest_asyncio
import websockets


# ── Configuration ─────────────────────────────────────────

def get_sut_config():
    """Get SUT connection config from environment."""
    return {
        "url": os.environ.get("SUT_URL", "http://localhost:8124"),
        "token": os.environ.get("SUT_TOKEN", ""),
        "mqtt_host": os.environ.get("SUT_MQTT_HOST", "localhost"),
        "mqtt_port": int(os.environ.get("SUT_MQTT_PORT", "1883")),
        "ws_url": os.environ.get("SUT_WS_URL", ""),
    }


# ── REST Client ───────────────────────────────────────────

class RESTClient:
    """HA-compatible REST API client for CTS tests."""

    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.AsyncClient(timeout=10.0)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def get_api_status(self) -> dict:
        resp = await self.client.get(f"{self.base_url}/api/", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_config(self) -> dict:
        resp = await self.client.get(f"{self.base_url}/api/config", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_states(self) -> list[dict]:
        resp = await self.client.get(f"{self.base_url}/api/states", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_state(self, entity_id: str) -> Optional[dict]:
        resp = await self.client.get(
            f"{self.base_url}/api/states/{entity_id}",
            headers=self._headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def set_state(self, entity_id: str, state: str,
                        attributes: Optional[dict] = None) -> dict:
        body = {"state": state}
        if attributes:
            body["attributes"] = attributes
        resp = await self.client.post(
            f"{self.base_url}/api/states/{entity_id}",
            headers=self._headers(),
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    async def call_service(self, domain: str, service: str,
                           data: Optional[dict] = None) -> list:
        resp = await self.client.post(
            f"{self.base_url}/api/services/{domain}/{service}",
            headers=self._headers(),
            json=data or {},
        )
        resp.raise_for_status()
        return resp.json()

    async def fire_event(self, event_type: str,
                         data: Optional[dict] = None) -> dict:
        resp = await self.client.post(
            f"{self.base_url}/api/events/{event_type}",
            headers=self._headers(),
            json=data or {},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_health(self) -> dict:
        resp = await self.client.get(
            f"{self.base_url}/api/health",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()


# ── WebSocket Client ──────────────────────────────────────

class WSClient:
    """HA-compatible WebSocket client for CTS tests."""

    def __init__(self, ws_url: str, token: str = ""):
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self._msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)
        # Receive auth_required
        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_required"

        # Send auth
        await self.ws.send(json.dumps({
            "type": "auth",
            "access_token": self.token or "test-token",
        }))

        # Receive auth_ok
        msg = json.loads(await self.ws.recv())
        assert msg["type"] == "auth_ok"
        return self

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def subscribe_events(self, event_type: str = "state_changed") -> int:
        msg_id = self._next_id()
        await self.ws.send(json.dumps({
            "id": msg_id,
            "type": "subscribe_events",
            "event_type": event_type,
        }))
        result = json.loads(await self.ws.recv())
        assert result["id"] == msg_id
        assert result["success"] is True
        return msg_id

    async def get_states(self) -> list:
        msg_id = self._next_id()
        await self.ws.send(json.dumps({
            "id": msg_id,
            "type": "get_states",
        }))
        result = json.loads(await self.ws.recv())
        assert result["id"] == msg_id
        assert result["success"] is True
        return result.get("result", [])

    async def recv_event(self, timeout: float = 5.0) -> dict:
        return json.loads(await asyncio.wait_for(self.ws.recv(), timeout))

    async def ping(self) -> bool:
        msg_id = self._next_id()
        await self.ws.send(json.dumps({
            "id": msg_id,
            "type": "ping",
        }))
        result = json.loads(await self.ws.recv())
        # HA returns type=pong, also accept type=result with success=true
        return result.get("type") == "pong" or result.get("success", False)

    async def close(self):
        if self.ws:
            await self.ws.close()


# ── MQTT Client ───────────────────────────────────────────

class MQTTClient:
    """Synchronous MQTT client wrapper for CTS tests."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"cts-{os.getpid()}")
        self._messages = {}
        self.client.on_message = self._on_message

    def _on_message(self, client, userdata, msg):
        self._messages[msg.topic] = msg.payload.decode()

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        return self

    def publish(self, topic: str, payload: str, retain: bool = True):
        self.client.publish(topic, payload, retain=retain)

    def subscribe(self, topic: str):
        self.client.subscribe(topic)

    def get_message(self, topic: str, timeout: float = 3.0) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if topic in self._messages:
                return self._messages.pop(topic)
            time.sleep(0.05)
        return None

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def sut_config():
    return get_sut_config()


@pytest_asyncio.fixture
async def rest(sut_config) -> AsyncGenerator[RESTClient, None]:
    client = RESTClient(sut_config["url"], sut_config["token"])
    yield client
    await client.close()


@pytest_asyncio.fixture
async def ws(sut_config) -> AsyncGenerator[WSClient, None]:
    ws_url = sut_config["ws_url"]
    if not ws_url:
        ws_url = sut_config["url"].replace("http://", "ws://").replace("https://", "wss://")
        ws_url += "/api/websocket"
    client = WSClient(ws_url, sut_config["token"])
    await client.connect()
    yield client
    await client.close()


@pytest.fixture
def mqtt_client(sut_config) -> MQTTClient:
    client = MQTTClient(sut_config["mqtt_host"], sut_config["mqtt_port"])
    client.connect()
    yield client
    client.disconnect()
