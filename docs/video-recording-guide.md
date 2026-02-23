# Video Recording Guide -- Innovation Week Demo

## Overview

4-segment pre-recorded demo video. Total runtime: ~8-10 minutes.

| Segment | Content | Duration |
|---------|---------|----------|
| 1 | Desktop side-by-side: HA vs Marge | ~4 min |
| 2 | Marge on Raspberry Pi 5 | ~2 min |
| 3 | HA on same Raspberry Pi 5 | ~2 min |
| 4 | Wrap-up narration | ~1 min |

## Pre-Recording Preparation

### Night Before

Build and deploy the ARM64 image for Pi segments:

```bash
# Build ARM64 image
docker buildx build --platform linux/arm64 -f marge-core/Dockerfile -t marge:pi --load .

# Option A: manual transfer
docker save marge:pi | gzip > /tmp/marge-pi.tar.gz
scp /tmp/marge-pi.tar.gz pi@PI_IP:/tmp/
ssh pi@PI_IP "docker load < /tmp/marge-pi.tar.gz"

# Option B: deploy script (handles build + transfer)
./scripts/pi-deploy.sh pi@PI_IP
```

### Day Of

Desktop checks:

```bash
docker compose up -d
curl localhost:8124/api/health                                    # Marge
curl -H "Authorization: Bearer TOKEN" localhost:8123/api/         # HA
open http://localhost:3000                                        # Dashboard
```

Pi checks:

```bash
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml up -d"
sleep 5 && curl PI_IP:8124/api/health
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml down"

ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml up -d"
sleep 90 && curl PI_IP:8123/api/
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml down"
```

Refresh the HA token (expires every ~30 min):

```bash
./scripts/ha-refresh-token.sh
```

### Screen Recording Setup

- OBS or similar, 1920x1080 resolution
- Dashboard in Chrome/Firefox, full-screen or windowed
- Terminal visible for commands (optional -- can hide for cleaner look)

## Segment 1: Desktop Side-by-Side (~4 min)

**What viewers see:** Dashboard at localhost:3000 showing HA vs Marge processing identical scenario events in real-time. ASCII house updating, memory/latency comparison bars, event log streaming.

### Setup

```bash
./scripts/run-demo.sh docker
open http://localhost:3000
```

### Recording

1. **Start recording** with dashboard visible.
2. Launch the highlight reel:
   ```bash
   ./scripts/run-demo.sh docker-highlight
   ```
3. **Narration during dawn chapter:**
   - "Both systems receive identical MQTT events from 44 virtual devices."
   - "Watch the memory bars -- HA uses 160MB, Marge uses 30MB."
   - "Latency: HA averages 23ms per API call, Marge averages 17 microseconds."
4. Let morning and sunset chapters play through.
5. **During goodnight chapter:** "Same automations, same scenes, same outcomes."
6. **Outage chapter** -- recovery race overlay appears automatically:
   - "Power outage simulation -- both systems killed, race to recover."
   - "Marge recovers in under 6 seconds. HA takes over 90."
7. **Score card** appears automatically after scenario completes (or press `S` to toggle):
   - "Final score card -- same events, same verifications, dramatically different resource usage."
8. **Stop recording.**

### If Something Goes Wrong

- HA not responding: `./scripts/ha-refresh-token.sh`
- Marge not responding: `docker compose restart marge`
- Dashboard stuck: hard refresh (Ctrl+Shift+R)
- Score card missing: press `S`

## Segment 2: Marge on Raspberry Pi (~2 min)

**What viewers see:** Dashboard in marge-only mode with "Raspberry Pi 5" hardware label. Single-column metrics. Scenario running against Pi hardware.

### Setup

```bash
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml up -d"
sleep 5
curl PI_IP:8124/api/health

open "http://localhost:3000?marge_ws=ws://PI_IP:8124/api/websocket&marge_rest=http://PI_IP:8124/api&mode=marge-only&label=Raspberry+Pi+5"
```

### Recording

1. **Start recording** with Pi dashboard visible. Note the "Raspberry Pi 5" label.
2. Run the dawn chapter against the Pi:
   ```bash
   TARGET=marge \
   MARGE_URL=http://PI_IP:8124 \
   MARGE_MQTT_HOST=PI_IP \
   MARGE_MQTT_PORT=1884 \
   SPEED=10 \
   CHAPTER=dawn \
   python3 scenario-driver/driver.py
   ```
3. **Narration:** "What about real hardware? Here's Marge running on an $80 Raspberry Pi 5. Same 44 devices, same automations. 30 megabytes of RAM."
4. Point out the metrics -- startup time, memory, latency all visible.
5. **Stop recording.**

### Cleanup

```bash
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-marge.yml down"
```

## Segment 3: HA on Same Pi (~2 min)

**What viewers see:** Dashboard in ha-only mode with "Raspberry Pi 5 (HA)" label. Same Pi, same devices, now running Home Assistant.

### Setup

```bash
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml up -d"
sleep 90
curl PI_IP:8123/api/

# NOTE: first run requires onboarding -- see Troubleshooting section

open "http://localhost:3000?ha_ws=ws://PI_IP:8123/api/websocket&ha_rest=http://PI_IP:8123/api&ha_token=HA_TOKEN&mode=ha-only&label=Raspberry+Pi+5+(HA)"
```

### Recording

1. **Start recording** with HA dashboard visible.
2. Run the dawn chapter against Pi HA:
   ```bash
   TARGET=ha \
   HA_URL=http://PI_IP:8123 \
   HA_TOKEN=HA_TOKEN \
   HA_MQTT_HOST=PI_IP \
   HA_MQTT_PORT=1883 \
   SPEED=10 \
   CHAPTER=dawn \
   python3 scenario-driver/driver.py
   ```
3. **Narration:** "Same Pi, same devices, now running Home Assistant. Notice the memory -- 160 megabytes vs Marge's 30. Startup took 90 seconds vs under one."
4. **Stop recording.**

### Cleanup

```bash
ssh pi@PI_IP "cd ~/marge-demo && docker compose -f docker-compose.pi-ha.yml down"
```

## Segment 4: Wrap-Up (~1 min)

**What viewers see:** Voiceover with text/slides, or narration over the score card from Segment 1.

### Narration Script

"A few things to acknowledge: this is a minimal smart home configuration -- 6 automations, 2 scenes, 44 virtual devices. The real HA ecosystem has thousands of integrations. But that's exactly the point.

For the core job -- receiving sensor data, evaluating automations, controlling devices -- a clean-room Rust implementation handles everything HA does, with a fraction of the resources. 77 conformance tests prove API compatibility at 99.6%.

Marge isn't trying to replace Home Assistant. It's exploring what home automation looks like when you start from scratch with modern systems programming. One binary. No Python runtime. No package manager. Just a 90MB Docker image that starts in milliseconds.

Built in one sitting. Nine and a half hours. Forty-seven commits."

## Troubleshooting

### HA Token Expired

```bash
./scripts/ha-refresh-token.sh
# Or create a long-lived token: HA UI -> Profile -> Long-Lived Access Tokens
```

### Pi Not Reachable

```bash
ping PI_IP
ssh pi@PI_IP "docker ps"
```

### Dashboard Shows "--" Everywhere

- Verify WebSocket URL in query params matches the running system's IP and port.
- Hard refresh the browser (Ctrl+Shift+R).

### HA Needs Onboarding (First Run on Pi)

1. Open http://PI_IP:8123 in a browser.
2. Complete the onboarding wizard (create account).
3. Go to Profile -> Long-Lived Access Tokens -> Create Token.
4. Use the token for the dashboard `ha_token=` param and driver `HA_TOKEN=` env var.

### Build Failed on ARM64

```bash
docker buildx create --use --name multiarch
docker buildx build --platform linux/arm64 -f marge-core/Dockerfile -t marge:pi --load .
```

## Quick Reference

| What | Command |
|------|---------|
| Start desktop demo | `./scripts/run-demo.sh docker-highlight` |
| Deploy to Pi | `./scripts/pi-deploy.sh pi@PI_IP` |
| Pi: Start Marge | `docker compose -f docker-compose.pi-marge.yml up -d` |
| Pi: Start HA | `docker compose -f docker-compose.pi-ha.yml up -d` |
| Pi: Stop all | `docker compose -f docker-compose.pi-*.yml down` |
| Dashboard (desktop) | `http://localhost:3000` |
| Dashboard (Pi Marge) | `...?marge_ws=ws://PI_IP:8124/api/websocket&marge_rest=http://PI_IP:8124/api&mode=marge-only&label=Raspberry+Pi+5` |
| Dashboard (Pi HA) | `...?ha_ws=ws://PI_IP:8123/api/websocket&ha_rest=http://PI_IP:8123/api&ha_token=TOKEN&mode=ha-only&label=Raspberry+Pi+5+(HA)` |
| Refresh HA token | `./scripts/ha-refresh-token.sh` |
| Toggle score card | Press `S` in dashboard |
