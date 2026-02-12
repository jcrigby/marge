#!/usr/bin/env python3
"""
MARGE Demo — Scenario Driver

Reads scenario.json and plays Day-in-the-Life events against one or both SUTs
(Home Assistant and/or Marge). Supports sim-time acceleration.

Usage:
    python driver.py [--speed 10] [--chapter dawn] [--target both|ha|marge]

Protocol (from ha-assumptions-deep-dive.md):
    - Sensor/binary_sensor state → MQTT publish to state_topic
    - Service calls (light.turn_on, etc.) → REST POST /api/services/...
    - Time/sun automations → REST POST /api/services/automation/trigger
    - sun.sun state → REST POST /api/states/sun.sun (non-MQTT entity)
    - Events (bedside_button) → REST POST /api/events/{event_type}
"""

import asyncio
import json
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
import paho.mqtt.client as mqtt


@dataclass
class SUTConnection:
    """Connection to a System Under Test (HA or Marge)."""
    name: str
    rest_url: str
    mqtt_host: str
    mqtt_port: int
    token: Optional[str] = None
    mqtt_client: Optional[mqtt.Client] = None
    http_client: Optional[httpx.AsyncClient] = None

    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h


@dataclass
class DriverState:
    """Tracks current entity states for the generator engine."""
    values: dict = field(default_factory=dict)


def load_scenario(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def connect_mqtt(host: str, port: int, client_id: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.connect(host, port, keepalive=60)
    client.loop_start()
    return client


def entity_to_mqtt_topic(entity_id: str) -> str:
    """Convert entity_id to its MQTT state topic.

    Maps entity IDs like 'sensor.bedroom_temperature' to MQTT topics like
    'home/sensor/bedroom_temperature/state'.
    """
    parts = entity_id.split(".", 1)
    if len(parts) != 2:
        return f"home/{entity_id}/state"
    domain, object_id = parts
    return f"home/{domain}/{object_id}/state"


async def push_state_mqtt(sut: SUTConnection, entity_id: str, state: str,
                          attributes: Optional[dict] = None):
    """Push sensor/binary_sensor state via MQTT (the correct way).
    Falls back to REST if MQTT not available."""
    if sut.mqtt_client:
        topic = entity_to_mqtt_topic(entity_id)
        sut.mqtt_client.publish(topic, state, retain=True)
    else:
        await push_state_rest(sut, entity_id, state, attributes)


async def push_state_rest(sut: SUTConnection, entity_id: str, state: str,
                          attributes: Optional[dict] = None):
    """Push state via REST API (for non-MQTT entities like sun.sun)."""
    body = {"state": state}
    if attributes:
        body["attributes"] = attributes
    try:
        await sut.http_client.post(
            f"{sut.rest_url}/api/states/{entity_id}",
            headers=sut.headers(),
            json=body,
            timeout=5.0,
        )
    except Exception as e:
        print(f"  [{sut.name}] REST push failed for {entity_id}: {e}")


async def call_service(sut: SUTConnection, domain: str, service: str,
                       data: Optional[dict] = None):
    """Call a service via REST API."""
    try:
        await sut.http_client.post(
            f"{sut.rest_url}/api/services/{domain}/{service}",
            headers=sut.headers(),
            json=data or {},
            timeout=10.0,
        )
    except Exception as e:
        print(f"  [{sut.name}] Service call failed {domain}.{service}: {e}")


async def fire_event(sut: SUTConnection, event_type: str,
                     data: Optional[dict] = None):
    """Fire an event via REST API."""
    try:
        await sut.http_client.post(
            f"{sut.rest_url}/api/events/{event_type}",
            headers=sut.headers(),
            json=data or {},
            timeout=5.0,
        )
    except Exception as e:
        print(f"  [{sut.name}] Event fire failed {event_type}: {e}")


async def trigger_automation(sut: SUTConnection, automation_id: str):
    """Force-fire an automation (bypasses conditions by default)."""
    await call_service(sut, "automation", "trigger", {
        "entity_id": f"automation.{automation_id}"
    })


async def verify_state(sut: SUTConnection, entity_id: str,
                       expected_state: Optional[str] = None,
                       expected_attributes: Optional[dict] = None,
                       timeout_ms: int = 5000):
    """Verify an entity has the expected state, polling until timeout."""
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        try:
            resp = await sut.http_client.get(
                f"{sut.rest_url}/api/states/{entity_id}",
                headers=sut.headers(),
                timeout=3.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                state_ok = expected_state is None or data.get("state") == expected_state
                attrs_ok = True
                if expected_attributes:
                    actual_attrs = data.get("attributes", {})
                    for k, v in expected_attributes.items():
                        if actual_attrs.get(k) != v:
                            attrs_ok = False
                            break
                if state_ok and attrs_ok:
                    print(f"  [{sut.name}] VERIFY OK: {entity_id} = {data.get('state')}")
                    return True
        except Exception:
            pass
        await asyncio.sleep(0.2)

    print(f"  [{sut.name}] VERIFY FAIL: {entity_id} "
          f"expected_state={expected_state} expected_attrs={expected_attributes}")
    return False


async def push_initial_state(suts: list[SUTConnection], scenario: dict):
    """Push all initial entity states to all SUTs via MQTT."""
    for entity in scenario.get("initial_state", []):
        eid = entity["entity_id"]
        state = entity["state"]
        attrs = entity.get("attributes", {})

        for sut in suts:
            domain = eid.split(".")[0]
            # MQTT entities: push via MQTT
            if domain in ("sensor", "binary_sensor", "light", "switch",
                          "lock", "climate", "alarm_control_panel"):
                await push_state_mqtt(sut, eid, state, attrs)
            else:
                # Non-MQTT entities (sun, weather, device_tracker, etc.): REST
                await push_state_rest(sut, eid, state, attrs)

    # Give MQTT time to propagate
    await asyncio.sleep(1.0)
    print(f"Initial state pushed: {len(scenario.get('initial_state', []))} entities")


class GeneratorEngine:
    """Procedural sensor noise generator for steady-state chapters."""

    def __init__(self, rules: list[dict], duration_ms: int, driver_state: DriverState):
        self.rules = rules
        self.duration_ms = duration_ms
        self.driver_state = driver_state

    def generate_events(self, all_entity_ids: list[str]) -> list[dict]:
        """Generate procedural events from rules."""
        events = []

        for rule in self.rules:
            pattern = rule["entity_pattern"]
            interval_ms = rule["interval_ms"]
            noise = rule["noise"]

            # Find matching entities
            regex = pattern.replace("*", ".*")
            matching = [eid for eid in all_entity_ids if re.match(regex, eid)]

            for eid in matching:
                t = 0
                while t < self.duration_ms:
                    value = self._generate_value(eid, noise, t)
                    if value is not None:
                        events.append({
                            "offset_ms": t,
                            "type": "state",
                            "entity_id": eid,
                            "state": str(round(value, 1) if isinstance(value, float) else value),
                            "attributes": {},
                        })
                        self.driver_state.values[eid] = value
                    t += interval_ms

        events.sort(key=lambda e: e["offset_ms"])
        return events

    def _generate_value(self, entity_id: str, noise: dict, t_ms: int) -> object:
        noise_type = noise["type"]
        current = self.driver_state.values.get(entity_id)

        if noise_type == "random_walk":
            if current is None:
                current = (noise.get("min", 0) + noise.get("max", 100)) / 2
            try:
                current = float(current)
            except (TypeError, ValueError):
                current = (noise.get("min", 0) + noise.get("max", 100)) / 2
            step = noise.get("step", 1.0)
            current += random.uniform(-step, step)
            current = max(noise.get("min", -999), min(noise.get("max", 999), current))
            return current

        elif noise_type == "sinusoidal":
            baseline = noise.get("baseline", 0)
            amplitude = noise.get("amplitude", 0)
            period = noise.get("period_ms", 3600000)
            return baseline + amplitude * math.sin(2 * math.pi * t_ms / period)

        elif noise_type == "curve":
            points = noise.get("points", [])
            if points:
                progress = t_ms / max(self.duration_ms, 1)
                # Linear interpolation between points
                for i in range(len(points) - 1):
                    x0, y0 = points[i]
                    x1, y1 = points[i + 1]
                    if x0 <= progress <= x1:
                        frac = (progress - x0) / max(x1 - x0, 0.001)
                        return y0 + frac * (y1 - y0)
                return points[-1][1]

            state_values = noise.get("state_values", [])
            if state_values:
                idx = int((t_ms / max(self.duration_ms, 1)) * len(state_values))
                idx = min(idx, len(state_values) - 1)
                return state_values[idx]

        elif noise_type == "stochastic":
            on_prob = noise.get("on_probability", 0.1)
            if random.random() < on_prob:
                return "on"
            return "off"

        elif noise_type == "derived":
            from_entity = noise.get("from")
            formula = noise.get("formula", "value")
            value = self.driver_state.values.get(from_entity, 0)
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0
            try:
                return eval(formula, {"value": value, "math": math})
            except Exception:
                return value

        return current


async def play_chapter(suts: list[SUTConnection], chapter_name: str,
                       chapter: dict, speed: float, scenario: dict,
                       driver_state: DriverState):
    """Play a single chapter of the scenario."""
    print(f"\n{'='*60}")
    print(f"CHAPTER: {chapter_name.upper()}")
    print(f"  {chapter.get('description', '')}")
    print(f"  Speed: {speed}x")
    print(f"{'='*60}")

    events = list(chapter.get("events", []))

    # If there's a generator, produce procedural events
    if "generator" in chapter:
        gen = chapter["generator"]
        all_eids = [e["entity_id"] for e in scenario.get("initial_state", [])]
        engine = GeneratorEngine(gen["rules"], gen["duration_ms"], driver_state)
        generated = engine.generate_events(all_eids)
        events.extend(generated)
        events.sort(key=lambda e: e["offset_ms"])
        print(f"  Generated {len(generated)} procedural events")

    last_offset = 0
    for event in events:
        offset = event["offset_ms"]

        # Wait for the right sim-time (adjusted for speed)
        wait_ms = (offset - last_offset) / speed
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)
        last_offset = offset

        etype = event["type"]

        if etype == "annotation":
            print(f"  [{offset/1000:.0f}s] {event['message']}")

        elif etype == "state":
            entity_id = event["entity_id"]
            state = event["state"]
            attrs = event.get("attributes", {})
            driver_state.values[entity_id] = state

            for sut in suts:
                domain = entity_id.split(".")[0]
                if domain in ("sun", "weather", "device_tracker", "person",
                              "button", "media_player"):
                    await push_state_rest(sut, entity_id, state, attrs)
                else:
                    await push_state_mqtt(sut, entity_id, state, attrs)

        elif etype == "time_tick":
            sim_time = event.get("sim_time", "")
            print(f"  [{offset/1000:.0f}s] SIM TIME: {sim_time}")
            # Force-trigger time-based automations at their scheduled times
            automations_to_fire = event.get("trigger_automations", [])
            for auto_id in automations_to_fire:
                for sut in suts:
                    await trigger_automation(sut, auto_id)

        elif etype == "fire_event":
            event_type = event["event_type"]
            event_data = event.get("data", {})
            print(f"  [{offset/1000:.0f}s] EVENT: {event_type}")
            for sut in suts:
                await fire_event(sut, event_type, event_data)

        elif etype == "sun":
            sun_event = event.get("event", "")
            print(f"  [{offset/1000:.0f}s] SUN: {sun_event}")
            # Force-trigger sun-based automations
            if sun_event == "sunset":
                for sut in suts:
                    await trigger_automation(sut, "sunset_lights")

        elif etype == "verify":
            entity_id = event["entity_id"]
            for sut in suts:
                await verify_state(
                    sut, entity_id,
                    expected_state=event.get("expected_state"),
                    expected_attributes=event.get("expected_attributes"),
                    timeout_ms=event.get("timeout_ms", 5000),
                )

        elif etype == "power_outage":
            print(f"\n  [{offset/1000:.0f}s] {'='*50}")
            print(f"  [{offset/1000:.0f}s] POWER OUTAGE — stopping all systems")
            print(f"  [{offset/1000:.0f}s] {'='*50}")
            await handle_power_outage(suts)

        elif etype == "power_restore":
            print(f"\n  [{offset/1000:.0f}s] {'='*50}")
            print(f"  [{offset/1000:.0f}s] POWER RESTORED — starting all systems")
            print(f"  [{offset/1000:.0f}s] {'='*50}")
            await handle_power_restore(suts)

        elif etype == "verify_system":
            system = event.get("system", "")
            timeout_ms = event.get("timeout_ms", 60000)
            await verify_system_online(suts, system, timeout_ms)

        elif etype == "collect_final_metrics":
            print(f"\n  [{offset/1000:.0f}s] {'='*50}")
            print(f"  [{offset/1000:.0f}s] FINAL METRICS")
            print(f"  [{offset/1000:.0f}s] {'='*50}")
            await collect_final_metrics(suts)


async def run_shell(cmd: str) -> tuple[int, str]:
    """Run a shell command and return (exit_code, output)."""
    import subprocess
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout + result.stderr


async def handle_power_outage(suts: list[SUTConnection]):
    """Stop all SUTs to simulate power outage."""
    for sut in suts:
        # Disconnect MQTT before stopping
        if sut.mqtt_client:
            try:
                sut.mqtt_client.loop_stop()
                sut.mqtt_client.disconnect()
            except Exception:
                pass
            sut.mqtt_client = None

    # Stop services via configured commands
    ha_stop = os.environ.get("HA_STOP_CMD", "docker stop marge-demo-ha")
    marge_stop = os.environ.get("MARGE_STOP_CMD", "pkill -9 marge")

    for sut in suts:
        if "ha" in sut.name.lower():
            print(f"  Stopping {sut.name}...")
            code, out = await run_shell(ha_stop)
            print(f"  {sut.name} stopped (exit={code})")
            sut._stop_time = time.monotonic()
        else:
            print(f"  Stopping {sut.name}...")
            code, out = await run_shell(marge_stop)
            print(f"  {sut.name} stopped (exit={code})")
            sut._stop_time = time.monotonic()


async def handle_power_restore(suts: list[SUTConnection]):
    """Restart all SUTs and begin measuring recovery time."""
    ha_start = os.environ.get("HA_START_CMD", "docker start marge-demo-ha")
    marge_start = os.environ.get("MARGE_START_CMD", "")

    for sut in suts:
        sut._restore_time = time.monotonic()
        if "ha" in sut.name.lower():
            print(f"  Starting {sut.name}...")
            code, out = await run_shell(ha_start)
            print(f"  {sut.name} start issued (exit={code})")
        else:
            if marge_start:
                print(f"  Starting {sut.name}...")
                code, out = await run_shell(marge_start)
                print(f"  {sut.name} start issued (exit={code})")
            else:
                print(f"  {sut.name}: no start command configured, assuming external restart")

    # Reconnect MQTT clients
    await asyncio.sleep(2)
    for sut in suts:
        try:
            client_id = f"marge-driver-{'ha' if 'ha' in sut.name.lower() else 'marge'}-restore"
            sut.mqtt_client = connect_mqtt(sut.mqtt_host, sut.mqtt_port, client_id)
        except Exception as e:
            print(f"  {sut.name} MQTT reconnect pending: {e}")


async def verify_system_online(suts: list[SUTConnection], system: str, timeout_ms: int):
    """Poll a specific system until it responds to health checks."""
    for sut in suts:
        name_lower = sut.name.lower()
        if system == "marge" and "marge" not in name_lower:
            continue
        if system == "ha" and "ha" not in name_lower:
            continue

        health_url = f"{sut.rest_url}/api/health" if "marge" in name_lower else f"{sut.rest_url}/api/"
        restore_time = getattr(sut, '_restore_time', time.monotonic())
        deadline = time.monotonic() + (timeout_ms / 1000)

        print(f"  Polling {sut.name} for recovery...")
        while time.monotonic() < deadline:
            try:
                resp = await sut.http_client.get(health_url, headers=sut.headers(), timeout=3.0)
                if resp.status_code == 200:
                    recovery_s = time.monotonic() - restore_time
                    print(f"  {sut.name} ONLINE — recovery time: {recovery_s:.1f}s")
                    sut._recovery_time = recovery_s
                    return True
            except Exception:
                pass
            await asyncio.sleep(1.0)

        elapsed = time.monotonic() - restore_time
        print(f"  {sut.name} STILL OFFLINE after {elapsed:.1f}s (timeout={timeout_ms/1000:.0f}s)")
        sut._recovery_time = None
        return False


async def collect_final_metrics(suts: list[SUTConnection]):
    """Collect and display final metrics from all SUTs."""
    print()
    for sut in suts:
        recovery = getattr(sut, '_recovery_time', None)
        recovery_str = f"{recovery:.1f}s" if recovery else "N/A"

        try:
            if "marge" in sut.name.lower():
                resp = await sut.http_client.get(
                    f"{sut.rest_url}/api/health", headers=sut.headers(), timeout=5.0)
                if resp.status_code == 200:
                    h = resp.json()
                    print(f"  {sut.name}:")
                    print(f"    Memory:       {h.get('memory_rss_mb', 0):.1f} MB")
                    print(f"    Entities:     {h.get('entity_count', 0)}")
                    print(f"    State changes: {h.get('state_changes', 0)}")
                    print(f"    Avg latency:  {h.get('latency_avg_us', 0):.2f} us")
                    print(f"    Max latency:  {h.get('latency_max_us', 0):.2f} us")
                    print(f"    Recovery:     {recovery_str}")
                    continue
            else:
                resp = await sut.http_client.get(
                    f"{sut.rest_url}/api/", headers=sut.headers(), timeout=5.0)
                if resp.status_code == 200:
                    print(f"  {sut.name}:")
                    print(f"    Status:       Online")
                    print(f"    Recovery:     {recovery_str}")
                    continue
        except Exception as e:
            pass
        print(f"  {sut.name}: Offline or unreachable (recovery: {recovery_str})")


async def main():
    speed = float(os.environ.get("SPEED", "10"))
    chapter_filter = os.environ.get("CHAPTER", "")
    target = os.environ.get("TARGET", "both")

    scenario_path = os.environ.get("SCENARIO_PATH", "./scenario.json")
    if not Path(scenario_path).exists():
        scenario_path = "/app/scenario.json"

    scenario = load_scenario(scenario_path)
    print(f"Loaded scenario: {scenario['metadata']['description']}")
    print(f"  Entities: {scenario['metadata']['entity_count']}")
    print(f"  Chapters: {', '.join(scenario['chapters'].keys())}")

    # Set up SUT connections
    suts = []

    if target in ("both", "ha"):
        ha_url = os.environ.get("HA_URL", "http://localhost:8123")
        ha_mqtt_host = os.environ.get("HA_MQTT_HOST", "localhost")
        ha_mqtt_port = int(os.environ.get("HA_MQTT_PORT", "1883"))
        ha_token = os.environ.get("HA_TOKEN", "")

        # Try reading token from file
        if not ha_token:
            for token_path in ["./ha-config/.ha_token", "/config/.ha_token"]:
                if Path(token_path).exists():
                    ha_token = Path(token_path).read_text().strip()
                    break

        ha = SUTConnection(
            name="HA-legacy",
            rest_url=ha_url,
            mqtt_host=ha_mqtt_host,
            mqtt_port=ha_mqtt_port,
            token=ha_token,
        )
        ha.http_client = httpx.AsyncClient()
        try:
            ha.mqtt_client = connect_mqtt(ha_mqtt_host, ha_mqtt_port, "marge-driver-ha")
        except Exception as e:
            print(f"WARNING: Could not connect to HA MQTT: {e}")
        suts.append(ha)

    if target in ("both", "marge"):
        marge_url = os.environ.get("MARGE_URL", "http://localhost:8124")
        marge_mqtt_host = os.environ.get("MARGE_MQTT_HOST", "localhost")
        marge_mqtt_port = int(os.environ.get("MARGE_MQTT_PORT", "1884"))

        marge = SUTConnection(
            name="Marge",
            rest_url=marge_url,
            mqtt_host=marge_mqtt_host,
            mqtt_port=marge_mqtt_port,
        )
        marge.http_client = httpx.AsyncClient()
        try:
            marge.mqtt_client = connect_mqtt(marge_mqtt_host, marge_mqtt_port, "marge-driver-marge")
        except Exception as e:
            print(f"WARNING: Could not connect to Marge MQTT: {e}")
        suts.append(marge)

    if not suts:
        print("ERROR: No SUTs configured")
        sys.exit(1)

    print(f"\nTargets: {', '.join(s.name for s in suts)}")

    # Push initial state
    await push_initial_state(suts, scenario)

    # Play chapters
    driver_state = DriverState()
    # Initialize driver state from initial_state
    for entity in scenario.get("initial_state", []):
        driver_state.values[entity["entity_id"]] = entity["state"]

    chapters = scenario["chapters"]
    chapter_order = ["dawn", "morning", "daytime", "sunset", "evening",
                     "goodnight", "night", "outage"]

    for ch_name in chapter_order:
        if ch_name not in chapters:
            continue
        if chapter_filter and ch_name != chapter_filter:
            continue
        await play_chapter(suts, ch_name, chapters[ch_name], speed, scenario, driver_state)

    # Cleanup
    for sut in suts:
        if sut.mqtt_client:
            sut.mqtt_client.loop_stop()
            sut.mqtt_client.disconnect()
        if sut.http_client:
            await sut.http_client.aclose()

    print("\n" + "="*60)
    print("SCENARIO COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
