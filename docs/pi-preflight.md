# Pi Dry-Run Pre-Flight Checklist

Pre-flight for the Raspberry Pi segments (2 and 3) of the Innovation Week demo.
For recording steps and narration scripts, see `docs/video-recording-guide.md`.

Replace `PI` below with your Pi's IP or hostname (e.g. `192.168.1.42`).

---

## Prerequisites (~5 min)

```bash
# 1. Pi is reachable and Docker is running
ssh pi@PI "docker info --format '{{.ServerVersion}}'"
# VERIFY: prints Docker version (e.g. 27.x)

# 2. docker buildx available on desktop
docker buildx version
# VERIFY: prints buildx version

# 3. Desktop dashboard container is built
docker compose build dashboard
# VERIFY: exits 0

# 4. Desktop scenario-driver deps installed
python3 -c "import aiohttp, paho.mqtt.client"
# VERIFY: no ImportError
```

---

## Night-Before Build (~45 min)

This is the slow step. Do it the night before.

```bash
# 1. Deploy to Pi (builds ARM64 image, transfers, syncs configs, smoke-tests)
./scripts/pi-deploy.sh pi@PI
# VERIFY: "Deployment Complete" with both health checks OK

# 2. Confirm marge:pi image on Pi
ssh pi@PI "docker images marge:pi --format '{{.Size}}'"
# VERIFY: prints ~90MB image size

# 3. Confirm config files landed
ssh pi@PI "ls ~/marge-demo/docker-compose.pi-*.yml"
# VERIFY: lists both pi-marge and pi-ha compose files
```

If pi-deploy.sh fails mid-way, fix the issue and re-run -- it is idempotent.

---

## Marge Segment Dry-Run (~3 min)

```bash
# 1. Start Marge stack on Pi
ssh pi@PI "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml up -d"
sleep 5

# 2. Health check
curl -sf http://PI:8124/api/health
# VERIFY: returns {"status":"ok"} or similar JSON

# 3. Open dashboard in marge-only mode (desktop browser)
#    URL: http://localhost:3000?marge_ws=ws://PI:8124/api/websocket&marge_rest=http://PI:8124/api&mode=marge-only&label=Raspberry+Pi+5
# VERIFY: dashboard loads, "Raspberry Pi 5" label visible, metrics not "--"

# 4. Run dawn chapter against Pi
TARGET=marge MARGE_URL=http://PI:8124 MARGE_MQTT_HOST=PI MARGE_MQTT_PORT=1884 \
  SPEED=10 CHAPTER=dawn python3 scenario-driver/driver.py
# VERIFY: events stream on dashboard, chapter completes without errors

# 5. Tear down Marge stack
ssh pi@PI "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml down"
# VERIFY: all containers stopped
```

---

## HA Segment Dry-Run (~5 min)

HA takes ~90s to start. Budget accordingly.

```bash
# 1. Start HA stack on Pi
ssh pi@PI "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml up -d"
sleep 90

# 2. API check
curl -sf http://PI:8123/api/
# VERIFY: returns JSON (if 401/403, HA is up but needs a token -- that's OK)
# NOTE: if this is the first run, complete onboarding first (see Troubleshooting)

# 3. Ensure you have a long-lived HA token
#    If not: open http://PI:8123 -> Profile -> Long-Lived Access Tokens -> Create
#    Store it as HA_TOKEN for the next steps

# 4. Open dashboard in ha-only mode (desktop browser)
#    URL: http://localhost:3000?ha_ws=ws://PI:8123/api/websocket&ha_rest=http://PI:8123/api&ha_token=HA_TOKEN&mode=ha-only&label=Raspberry+Pi+5+(HA)
# VERIFY: dashboard loads with HA data, "Raspberry Pi 5 (HA)" label visible

# 5. Run dawn chapter against Pi HA
TARGET=ha HA_URL=http://PI:8123 HA_TOKEN=HA_TOKEN HA_MQTT_HOST=PI HA_MQTT_PORT=1883 \
  SPEED=10 CHAPTER=dawn python3 scenario-driver/driver.py
# VERIFY: events stream on dashboard, chapter completes without errors

# 6. Tear down HA stack
ssh pi@PI "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml down"
# VERIFY: all containers stopped
```

---

## Teardown (~1 min)

```bash
# Confirm nothing is still running on Pi
ssh pi@PI "docker ps --format '{{.Names}}'"
# VERIFY: empty output (no running containers)
```

---

## Troubleshooting

**Marge health check fails:**
Wait another 10s. Check logs: `ssh pi@PI "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml logs marge --tail 30"`

**HA API returns 401/403:**
Create a long-lived token via the HA web UI at `http://PI:8123/profile`.

**HA needs onboarding (first run):**
Open `http://PI:8123` in a browser, complete the wizard, create a long-lived token under Profile.

**Dashboard shows "--" everywhere:**
Confirm the IP in the URL query params matches the Pi. Hard-refresh with Ctrl+Shift+R.

**Port conflict on Pi:**
Only one stack at a time -- both use port 1883 for Mosquitto. Always `down` one before starting the other.

**ARM64 build fails on desktop:**
Run `docker buildx create --use --name multiarch` then retry `pi-deploy.sh`.

**Driver can't reach Pi MQTT:**
Confirm port 1884 (Marge) or 1883 (HA) is reachable: `nc -zv PI 1884`
