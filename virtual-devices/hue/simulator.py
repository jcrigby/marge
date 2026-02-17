"""Virtual Philips Hue Bridge simulator.

Serves a fake Hue Bridge on port 8181 with 3 lights and 2 sensors.
Implements the subset of the Hue REST API that Marge's hue.rs integration
actually polls, so the integration discovers real-looking devices.

Auto-pairs: any POST /api with a devicetype body returns success.
"""

import asyncio
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── Bridge config ─────────────────────────────────────────────────────

BRIDGE_CONFIG = {
    "name": "Virtual Hue Bridge",
    "modelid": "BSB002",
    "swversion": "1953188020",
    "bridgeid": "001788FFFE123456",
    "apiversion": "1.50.0",
}

AUTO_USERNAME = "virtual-hue-user"

# ── Light state ───────────────────────────────────────────────────────

lights = {
    "1": {
        "name": "Den Lamp",
        "type": "Extended color light",
        "modelid": "LCT016",
        "manufacturername": "Signify",
        "uniqueid": "00:17:88:01:12:34:56:01-01",
        "state": {
            "on": False,
            "bri": 0,
            "ct": 370,
            "xy": [0.4573, 0.41],
            "reachable": True,
        },
    },
    "2": {
        "name": "Reading Light",
        "type": "Dimmable light",
        "modelid": "LWB014",
        "manufacturername": "Signify",
        "uniqueid": "00:17:88:01:12:34:56:01-02",
        "state": {
            "on": False,
            "bri": 0,
            "reachable": True,
        },
    },
    "3": {
        "name": "Accent Strip",
        "type": "Color light",
        "modelid": "LST002",
        "manufacturername": "Signify",
        "uniqueid": "00:17:88:01:12:34:56:01-03",
        "state": {
            "on": False,
            "bri": 0,
            "xy": [0.3227, 0.329],
            "reachable": True,
        },
    },
}

# ── Sensor state ──────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


sensors = {
    "1": {
        "name": "Den Motion",
        "type": "ZLLPresence",
        "modelid": "SML001",
        "manufacturername": "Signify",
        "uniqueid": "00:17:88:01:12:34:56:02-02-0406",
        "state": {
            "presence": False,
            "lastupdated": "2024-01-01T00:00:00",
        },
    },
    "2": {
        "name": "Den Temperature",
        "type": "ZLLTemperature",
        "modelid": "SML001",
        "manufacturername": "Signify",
        "uniqueid": "00:17:88:01:12:34:56:02-02-0402",
        "state": {
            "temperature": 2250,
            "lastupdated": "2024-01-01T00:00:00",
        },
    },
}

# Track when motion was last triggered so we can auto-clear after 30s
_motion_triggered_at: float | None = None

_lock = asyncio.Lock()


# ── Background drift task ─────────────────────────────────────────────

async def _drift_loop():
    """Every 5 seconds, drift temperature and randomly trigger motion."""
    global _motion_triggered_at

    while True:
        await asyncio.sleep(5)
        async with _lock:
            # Temperature drift: +/-25 in Hue units (1/100 C), range 1800-2800
            temp_state = sensors["2"]["state"]
            temp_state["temperature"] = max(1800, min(2800,
                temp_state["temperature"] + random.randint(-25, 25)))
            temp_state["lastupdated"] = _now_iso()

            # Motion sensor: 5% chance to trigger per tick
            motion_state = sensors["1"]["state"]
            now = time.time()

            if _motion_triggered_at is not None and now - _motion_triggered_at >= 30.0:
                # Auto-clear after 30 seconds
                motion_state["presence"] = False
                motion_state["lastupdated"] = _now_iso()
                _motion_triggered_at = None

            if not motion_state["presence"] and random.random() < 0.05:
                motion_state["presence"] = True
                motion_state["lastupdated"] = _now_iso()
                _motion_triggered_at = now


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_drift_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ── FastAPI app ───────────────────────────────────────────────────────

app = FastAPI(title="Virtual Hue Bridge Simulator", lifespan=lifespan)


# ── Pairing ───────────────────────────────────────────────────────────

@app.post("/api")
async def pair(request: Request):
    """POST /api -- auto-pair any client that sends a devicetype."""
    body = await request.json()
    devicetype = body.get("devicetype", "unknown")
    _ = devicetype  # accept any value
    return JSONResponse(content=[{"success": {"username": AUTO_USERNAME}}])


# ── Bridge config ─────────────────────────────────────────────────────

@app.get("/api/{username}/config")
async def get_config(username: str):
    """GET /api/{username}/config -- bridge configuration."""
    return JSONResponse(content=BRIDGE_CONFIG)


# ── Lights ────────────────────────────────────────────────────────────

@app.get("/api/{username}/lights")
async def get_lights(username: str):
    """GET /api/{username}/lights -- all lights keyed by string ID."""
    async with _lock:
        return JSONResponse(content=lights)


@app.get("/api/{username}/lights/{light_id}")
async def get_light(username: str, light_id: str):
    """GET /api/{username}/lights/{id} -- single light."""
    async with _lock:
        if light_id not in lights:
            return JSONResponse(
                status_code=404,
                content=[{"error": {"type": 3, "address": f"/lights/{light_id}",
                          "description": "resource not available"}}],
            )
        return JSONResponse(content=lights[light_id])


@app.put("/api/{username}/lights/{light_id}/state")
async def set_light_state(username: str, light_id: str, request: Request):
    """PUT /api/{username}/lights/{id}/state -- control a light.

    Accepts JSON body with on, bri, ct, xy, transitiontime.
    Returns Hue-style success array.
    """
    async with _lock:
        if light_id not in lights:
            return JSONResponse(
                status_code=404,
                content=[{"error": {"type": 3, "address": f"/lights/{light_id}",
                          "description": "resource not available"}}],
            )

        body = await request.json()
        light_state = lights[light_id]["state"]
        results = []

        if "on" in body:
            light_state["on"] = bool(body["on"])
            results.append({"success": {f"/lights/{light_id}/state/on": light_state["on"]}})

        if "bri" in body:
            light_state["bri"] = max(0, min(254, int(body["bri"])))
            results.append({"success": {f"/lights/{light_id}/state/bri": light_state["bri"]}})

        if "ct" in body:
            light_state["ct"] = int(body["ct"])
            results.append({"success": {f"/lights/{light_id}/state/ct": light_state["ct"]}})

        if "xy" in body:
            xy = body["xy"]
            if isinstance(xy, list) and len(xy) == 2:
                light_state["xy"] = [float(xy[0]), float(xy[1])]
                results.append({"success": {f"/lights/{light_id}/state/xy": light_state["xy"]}})

        if "transitiontime" in body:
            # transitiontime is accepted but not simulated (instant)
            results.append({"success": {
                f"/lights/{light_id}/state/transitiontime": int(body["transitiontime"])
            }})

        return JSONResponse(content=results)


# ── Sensors ───────────────────────────────────────────────────────────

@app.get("/api/{username}/sensors")
async def get_sensors(username: str):
    """GET /api/{username}/sensors -- all sensors keyed by string ID."""
    async with _lock:
        return JSONResponse(content=sensors)


@app.get("/api/{username}/sensors/{sensor_id}")
async def get_sensor(username: str, sensor_id: str):
    """GET /api/{username}/sensors/{id} -- single sensor."""
    async with _lock:
        if sensor_id not in sensors:
            return JSONResponse(
                status_code=404,
                content=[{"error": {"type": 3, "address": f"/sensors/{sensor_id}",
                          "description": "resource not available"}}],
            )
        return JSONResponse(content=sensors[sensor_id])


# ── Full state (convenience) ──────────────────────────────────────────

@app.get("/api/{username}")
async def get_full_state(username: str):
    """GET /api/{username} -- full bridge state (lights + sensors + config)."""
    async with _lock:
        return JSONResponse(content={
            "config": BRIDGE_CONFIG,
            "lights": lights,
            "sensors": sensors,
        })
