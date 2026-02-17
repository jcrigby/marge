"""Virtual Shelly Gen2 device simulator.

Serves two multiplexed Shelly Gen2 devices on a single FastAPI instance
(port 8180). Select device via ?dev=1 (default) or ?dev=2.

Device 1: shellyplus1pm  -- relay with power monitoring
Device 2: shellydimmer2  -- dimmer with brightness control

Endpoints mirror the real Shelly Gen2 local HTTP API so that Marge's
shelly.rs integration poller discovers real-looking devices.
"""

import asyncio
import random
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

# ── Device state ──────────────────────────────────────────────────────

START_TIME = time.time()

# Device 1: Kitchen Relay (shellyplus1pm)
device1 = {
    "identity": {
        "name": "Kitchen Relay",
        "id": "shellyplus1pm-aabbccddeeff",
        "mac": "AABBCCDDEEFF",
        "gen": 2,
        "fw_id": "20240101-000000/1.0.0-virtual",
    },
    "switch": {
        "output": False,
        "apower": 0.0,
        "voltage": 120.1,
        "current": 0.0,
        "temperature_c": 42.5,
        "energy_total": 150.0,
    },
}

# Device 2: Hallway Dimmer (shellydimmer2)
device2 = {
    "identity": {
        "name": "Hallway Dimmer",
        "id": "shellydimmer2-112233445566",
        "mac": "112233445566",
        "gen": 2,
        "fw_id": "20240101-000000/1.0.0-virtual",
    },
    "light": {
        "output": False,
        "brightness": 0,
    },
}

_lock = asyncio.Lock()


def _get_device(dev: int):
    """Return the device dict for the given selector."""
    if dev == 2:
        return device2
    return device1


# ── Background drift task ─────────────────────────────────────────────

async def _drift_loop():
    """Every 5 seconds, drift analog readings to simulate real hardware."""
    while True:
        await asyncio.sleep(5)
        async with _lock:
            sw = device1["switch"]
            # Power: 50-200 W when on, ~0 when off
            if sw["output"]:
                sw["apower"] = max(50.0, min(200.0,
                    sw["apower"] + random.uniform(-5.0, 5.0)))
            else:
                sw["apower"] = max(0.0, min(2.0,
                    random.uniform(-0.1, 0.5)))

            # Voltage: 118-122 V
            sw["voltage"] = max(118.0, min(122.0,
                sw["voltage"] + random.uniform(-0.2, 0.2)))

            # Current = power / voltage
            if sw["voltage"] > 0:
                sw["current"] = round(sw["apower"] / sw["voltage"], 3)
            else:
                sw["current"] = 0.0

            # Temperature: 40-55 C
            sw["temperature_c"] = max(40.0, min(55.0,
                sw["temperature_c"] + random.uniform(-0.3, 0.3)))

            # Energy accumulates: power (W) * 5s / 3600 = Wh increment
            sw["energy_total"] += sw["apower"] * 5.0 / 3600.0


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

app = FastAPI(title="Virtual Shelly Simulator", lifespan=lifespan)


@app.get("/shelly")
async def shelly_identity(dev: int = Query(1)):
    """GET /shelly -- device identity (Gen2 format)."""
    device = _get_device(dev)
    return JSONResponse(content=device["identity"])


@app.get("/rpc/Shelly.GetStatus")
async def get_status(dev: int = Query(1)):
    """GET /rpc/Shelly.GetStatus -- full device status."""
    device = _get_device(dev)
    uptime = int(time.time() - START_TIME)

    async with _lock:
        if dev == 2:
            lt = device["light"]
            return JSONResponse(content={
                "sys": {"uptime": uptime, "ram_free": 35000},
                "light:0": {
                    "output": lt["output"],
                    "brightness": lt["brightness"],
                },
            })
        else:
            sw = device["switch"]
            return JSONResponse(content={
                "sys": {"uptime": uptime, "ram_free": 38000},
                "switch:0": {
                    "id": 0,
                    "output": sw["output"],
                    "apower": round(sw["apower"], 1),
                    "voltage": round(sw["voltage"], 1),
                    "current": round(sw["current"], 3),
                    "temperature": {
                        "tC": round(sw["temperature_c"], 1),
                        "tF": round(sw["temperature_c"] * 9.0 / 5.0 + 32.0, 1),
                    },
                    "aenergy": {
                        "total": round(sw["energy_total"], 1),
                    },
                },
            })


@app.get("/rpc/Switch.Set")
async def switch_set(id: int = Query(0), on: bool = Query(False)):
    """GET /rpc/Switch.Set?id=0&on=true|false -- control relay on device 1."""
    async with _lock:
        sw = device1["switch"]
        was_on = sw["output"]
        sw["output"] = on
        # When turning on, seed power to a reasonable value if near zero
        if on and sw["apower"] < 10.0:
            sw["apower"] = random.uniform(80.0, 120.0)
        # When turning off, drop power toward zero
        if not on:
            sw["apower"] = 0.0
            sw["current"] = 0.0
    return JSONResponse(content={"was_on": was_on})


@app.get("/rpc/Light.Set")
async def light_set(
    id: int = Query(0),
    on: bool = Query(False),
    brightness: int = Query(None),
):
    """GET /rpc/Light.Set?id=0&on=true|false&brightness=0-100 -- control dimmer on device 2."""
    async with _lock:
        lt = device2["light"]
        was_on = lt["output"]
        lt["output"] = on
        if brightness is not None:
            lt["brightness"] = max(0, min(100, brightness))
        elif on and lt["brightness"] == 0:
            lt["brightness"] = 100
        elif not on:
            lt["brightness"] = 0
    return JSONResponse(content={"was_on": was_on})


@app.get("/rpc/Switch.Toggle")
async def switch_toggle(id: int = Query(0)):
    """GET /rpc/Switch.Toggle?id=0 -- toggle relay on device 1."""
    async with _lock:
        sw = device1["switch"]
        was_on = sw["output"]
        sw["output"] = not sw["output"]
        if sw["output"] and sw["apower"] < 10.0:
            sw["apower"] = random.uniform(80.0, 120.0)
        if not sw["output"]:
            sw["apower"] = 0.0
            sw["current"] = 0.0
    return JSONResponse(content={"was_on": was_on})


@app.get("/devices")
async def list_devices():
    """GET /devices -- list both virtual devices (convenience endpoint)."""
    return JSONResponse(content={
        "devices": [
            {"dev": 1, **device1["identity"]},
            {"dev": 2, **device2["identity"]},
        ]
    })
