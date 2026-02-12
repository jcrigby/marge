# MARGE Ã¢â‚¬â€ Theory of Operations (TheoryOps)

**Document Number:** MRG-OPS-001  
**Version:** 0.1.0-DRAFT  
**Classification:** UNCLASSIFIED // FOUO  
**Date:** 2026-02-12  
**Parent Documents:** MRG-SSS-001 (System Spec), MRG-CTS-001 (Test Suite)  
**Prepared For:** The Department of Not Running Python In Production  

---

## 0. WHAT THIS DOCUMENT IS

The SSS says what to build. The CTS says how to prove it works. This document says **how it lives.**

A smarthome platform is not a web app. It doesn't get deployed, demoed, and forgotten. It runs 24/7/365 on hardware in someone's closet, controlling physical systems that affect safety, comfort, and security. It must:

- Start automatically after a power outage at 3 AM
- Survive a corrupted SD card gracefully
- Let a non-technical spouse check the front door camera
- Not lose a week of energy data because an update went sideways
- Keep the door locks working when the WiFi goes down
- Be updated without taking the house offline for 10 minutes

This document describes how Marge operates in the real world: how it's deployed, how it runs day-to-day, how it fails, how it recovers, how it's maintained, and how people interact with it across its entire lifecycle.

The audience is the operator Ã¢â‚¬â€ which, for a smarthome, is usually the same person who installed it. They're technical enough to run Docker but too busy to babysit a system every weekend.

---

## 1. OPERATIONAL CONCEPT

### 1.1 A Day in the Life

Here is what Marge does on an ordinary Tuesday:

```
05:30  Morning automation evaluates. Sun position calculated. 
       Bedroom lights ramp to 20% warm white over 10 minutes.
       Thermostat setpoint changes from 66Ã‚Â°F (night) to 70Ã‚Â°F (day).
       Coffee maker switch turns on via Z-Wave.
       Ã¢â€ â€™ 4 state changes, 3 service calls, 1 automation trace logged.
       Ã¢â€ â€™ Total time: 12ms.

06:15  Front door opens. Z-Wave lock reports "unlocked" via local push.
       Motion sensor in entryway fires. Automation: if armed_away Ã¢â€ â€™ alert.
       System is in "home" mode Ã¢â€ â€™ no alert. State logged.
       Ã¢â€ â€™ 2 state changes, 1 condition evaluated (false). 0 actions.

06:15Ã¢â‚¬â€œ17:00  System processes ~2,000 state changes from:
       - 14 temperature/humidity sensors reporting every 60s
       - 4 motion sensors reporting presence changes
       - 3 door/window sensors
       - Energy monitoring (power, voltage, current every 10s)
       - Weather integration polling every 30 minutes
       - Device tracker updates from phone WiFi
       Ã¢â€ â€™ All state changes persisted to SQLite.
       Ã¢â€ â€™ 24-hour history available for dashboard graphs.
       Ã¢â€ â€™ Hourly statistics computed for energy sensors.

17:30  Sunset trigger fires (calculated from lat/long).
       Exterior lighting automation activates.
       Living room scene "Evening" applied (4 lights, 1 media player).
       Ã¢â€ â€™ 6 state changes, 1 automation trace.

22:00  "Goodnight" scene activated via bedside button (Zigbee).
       All lights off. Doors verified locked. Thermostat to night mode.
       Alarm panel set to armed_night.
       Ã¢â€ â€™ 12 state changes, verification automation confirms all locks.
       Ã¢â€ â€™ If any lock reports unlocked Ã¢â€ â€™ notification to phone.

22:00Ã¢â‚¬â€œ05:30  System in quiet mode. 
       Smoke/CO sensors monitored continuously (Z-Wave push).
       Motion sensors active for security automations.
       State changes: ~200 (mostly sensor readings).
       Memory stable. CPU near idle. MQTT broker heartbeating.

03:47  Power outage. UPS holds for 15 minutes. 
       Marge writes final state to SQLite (WAL flush).
       Clean shutdown logged.

03:48  Power restored. Raspberry Pi boots.
       Marge binary starts in 400ms.
       Integration processes spawn over next 2 seconds.
       State restored from SQLite. 
       MQTT broker accepts reconnections from ESP devices.
       Z-Wave controller re-interviews failed nodes.
       All entities report current state within 30 seconds.
       Ã¢â€ â€™ Total recovery: <35 seconds from power-on to fully operational.
       Ã¢â€ â€™ HA-legacy equivalent: 90-180 seconds.
```

### 1.2 System Context

```
                            Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
                            Ã¢â€â€š      Internet        Ã¢â€â€š
                            Ã¢â€â€š  (optional, for:     Ã¢â€â€š
                            Ã¢â€â€š   cloud integrations,Ã¢â€â€š
                            Ã¢â€â€š   remote access,     Ã¢â€â€š
                            Ã¢â€â€š   push notifications)Ã¢â€â€š
                            Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                                       Ã¢â€â€š
                              Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
                              Ã¢â€â€š   Router/NAT    Ã¢â€â€š
                              Ã¢â€â€š   DHCP Server   Ã¢â€â€š
                              Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                                       Ã¢â€â€š
               Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
               Ã¢â€â€š                       Ã¢â€â€š                        Ã¢â€â€š
     Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â   Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â    Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
     Ã¢â€â€š   WiFi Devices     Ã¢â€â€š   Ã¢â€â€š  MARGE HOST Ã¢â€â€š    Ã¢â€â€š  Wired Devices     Ã¢â€â€š
     Ã¢â€â€š                    Ã¢â€â€š   Ã¢â€â€š                Ã¢â€â€š    Ã¢â€â€š                    Ã¢â€â€š
     Ã¢â€â€š Ã¢â‚¬Â¢ ESP32 sensors    Ã¢â€â€š   Ã¢â€â€š Ã¢â‚¬Â¢ Rust Core    Ã¢â€â€š    Ã¢â€â€š Ã¢â‚¬Â¢ Z-Wave stick     Ã¢â€â€š
     Ã¢â€â€š Ã¢â‚¬Â¢ Smart plugs      Ã¢â€â€š   Ã¢â€â€š Ã¢â‚¬Â¢ MQTT Broker  Ã¢â€â€š    Ã¢â€â€š Ã¢â‚¬Â¢ Zigbee dongle    Ã¢â€â€š
     Ã¢â€â€š Ã¢â‚¬Â¢ Cameras (RTSP)   Ã¢â€â€š   Ã¢â€â€š Ã¢â‚¬Â¢ Integrations Ã¢â€â€š    Ã¢â€â€š Ã¢â‚¬Â¢ PoE cameras      Ã¢â€â€š
     Ã¢â€â€š Ã¢â‚¬Â¢ Phones (tracker) Ã¢â€â€š   Ã¢â€â€š Ã¢â‚¬Â¢ Web UI       Ã¢â€â€š    Ã¢â€â€š Ã¢â‚¬Â¢ Wired sensors    Ã¢â€â€š
     Ã¢â€â€š Ã¢â‚¬Â¢ Voice assistants Ã¢â€â€š   Ã¢â€â€š Ã¢â‚¬Â¢ SQLite DB    Ã¢â€â€š    Ã¢â€â€š                    Ã¢â€â€š
     Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                                       Ã¢â€â€š
                              Communicates via:
                              Ã¢â‚¬Â¢ MQTT (WiFi devices)
                              Ã¢â‚¬Â¢ Serial/USB (Z-Wave, Zigbee)
                              Ã¢â‚¬Â¢ HTTP/REST (cameras, APIs)
                              Ã¢â‚¬Â¢ WebSocket (frontend, integrations)
                              Ã¢â‚¬Â¢ mDNS/SSDP (discovery)
```

### 1.3 Operational Modes

| Mode | Description | Trigger | Behavior |
|---|---|---|---|
| **Normal** | All systems operational | Default | Full functionality, all integrations running |
| **Degraded** | Some integrations unavailable | Integration crash, network loss | Core continues. Affected entities marked `unavailable`. Automations with unavailable entities log warnings but don't block unrelated automations. |
| **Offline** | No internet connectivity | WAN outage | All local devices continue normally. Cloud integrations suspended. Push notifications queued (if supported) or dropped. |
| **Safe Mode** | Minimal operation, no custom config | Corrupted config, boot flag | Core starts with empty config. REST/WebSocket API available. Admin can upload corrected config via API or UI. |
| **Recovery** | Post-failure state restoration | Power loss, crash | State restored from SQLite. Integrations reconnect. Timers recalculated. |
| **Maintenance** | System update in progress | Operator-initiated | Active automations complete. New triggers deferred. State flushed. Binary replaced. Restart. |

---

## 2. DEPLOYMENT

### 2.1 Reference Platforms

| Platform | Hardware | OS | Notes |
|---|---|---|---|
| **Raspberry Pi 4/5** (recommended for most users) | 2-4GB RAM, 32GB+ SD or SSD via USB | Raspberry Pi OS Lite (64-bit) | Use SSD for reliability. SD cards fail under constant SQLite writes. |
| **Mini PC / NUC** | 4-8GB RAM, 128GB+ SSD | Ubuntu Server 24.04, Debian 12 | Best performance. Overkill for most homes. |
| **NAS (Synology, QNAP)** | Varies | Docker on NAS OS | Ensure USB passthrough works for Z-Wave/Zigbee sticks. |
| **VM (Proxmox, ESXi)** | 2+ vCPU, 2GB+ RAM | Any Linux | Pass through USB devices to VM. Avoid WiFi-based protocols in VM. |
| **Old Laptop** | Anything from last 10 years | Ubuntu Server | Surprisingly good option. Built-in battery = free UPS. |

### 2.2 Installation Methods

#### Method 1: Single Binary (Recommended for bare metal)

```bash
# Download
curl -L https://github.com/marge-home/marge/releases/latest/download/marge-linux-arm64 \
  -o /usr/local/bin/marge
chmod +x /usr/local/bin/marge

# Create data directory
mkdir -p /var/lib/marge
mkdir -p /etc/marge

# Generate default config
marge init --config /etc/marge/configuration.toml

# Install systemd service
marge install-service

# Start
systemctl start marge
systemctl enable marge

# Verify
curl http://localhost:8123/api/
```

**That's it.** One binary. One config file. One data directory. No Python. No virtualenv. No Docker. No Node.js. No `pip install --break-system-packages`.

#### Method 2: Docker (Recommended for NAS/VM)

```yaml
# docker-compose.yml
version: '3.8'
services:
  marge:
    image: ghcr.io/marge-home/marge:latest
    container_name: marge
    restart: unless-stopped
    network_mode: host          # Required for mDNS discovery
    volumes:
      - ./config:/etc/marge  # Configuration
      - ./data:/var/lib/marge # Database, state
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0  # Z-Wave stick
      - /dev/ttyUSB1:/dev/ttyUSB1  # Zigbee dongle
    environment:
      - TZ=America/Denver
```

```bash
docker compose up -d
```

#### Method 3: Marge OS (Future Ã¢â‚¬â€ Raspberry Pi image)

A pre-built SD card image with:
- Minimal Linux (buildroot or Alpine)
- Marge pre-installed and configured
- Web-based first-run wizard
- Automatic updates via A/B partition scheme

This is the "flash and forget" option for non-technical users. Not in Phase 1 scope.

### 2.3 First Run

```
1. Marge starts Ã¢â€ â€™ detects no configuration Ã¢â€ â€™ enters Setup Mode
2. Web UI available at http://marge.local:8123
3. Setup wizard:
   a. Create admin account (username/password)
   b. Set location (lat/long/timezone/elevation) Ã¢â‚¬â€ auto-detected if online
   c. Set unit system (imperial/metric)
   d. Detect USB devices (Z-Wave stick? Zigbee dongle?)
   e. Scan network for discoverable devices (mDNS, SSDP, MQTT)
   f. Present discovered devices Ã¢â€ â€™ user selects which to add
4. Configuration written to /etc/marge/configuration.toml
5. System enters Normal mode
```

### 2.4 Directory Structure

```
/etc/marge/                  # Configuration (backed up)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ configuration.toml          # Core system config (native)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ configuration.yaml          # HA-compatible config (if migrated)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ automations.yaml            # Automation definitions
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ scenes.yaml                 # Scene definitions  
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ scripts.yaml                # Script definitions
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ secrets.yaml                # Encrypted secrets
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ blueprints/                 # Blueprint templates
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ automation/
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ script/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ custom_cards/               # Custom frontend cards
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ integrations/               # Integration-specific config
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ zwave.toml
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ zigbee.toml
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ mqtt.toml

/var/lib/marge/              # Runtime data (backed up)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ marge.db                 # SQLite database (state, history, registry)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ marge.db-wal             # SQLite WAL file
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ marge.db-shm             # SQLite shared memory
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ backups/                    # Automatic backups
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ 2026-02-12_daily.tar.gz
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ 2026-02-05_weekly.tar.gz
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ tls/                        # TLS certificates (if generated)
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ integrations/               # Integration runtime data
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ zwave/                  # Z-Wave network keys, NVM backup
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ zigbee/                 # Zigbee network data

/var/log/marge/              # Logs (rotated, not backed up)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ marge.log                # Main application log
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ marge.log.1.gz           # Rotated logs
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ integrations/               # Per-integration logs
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ zwave.log
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ zigbee.log

/usr/local/bin/marge         # The binary (single file)
```

---

## 3. NORMAL OPERATIONS

### 3.1 Process Architecture

```
                    PID 1 (or systemd-managed)
                              Ã¢â€â€š
                    Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
                    Ã¢â€â€š   marge (main)   Ã¢â€â€š
                    Ã¢â€â€š                     Ã¢â€â€š
                    Ã¢â€â€š  Ã¢â‚¬Â¢ MQTT broker      Ã¢â€â€š  Ã¢â€ Â Embedded, port 1883
                    Ã¢â€â€š  Ã¢â‚¬Â¢ State machine    Ã¢â€â€š
                    Ã¢â€â€š  Ã¢â‚¬Â¢ Event bus        Ã¢â€â€š
                    Ã¢â€â€š  Ã¢â‚¬Â¢ Automation engineÃ¢â€â€š
                    Ã¢â€â€š  Ã¢â‚¬Â¢ HTTP/WS server   Ã¢â€â€š  Ã¢â€ Â Port 8123
                    Ã¢â€â€š  Ã¢â‚¬Â¢ Recorder         Ã¢â€â€š  Ã¢â€ Â SQLite writer
                    Ã¢â€â€š  Ã¢â‚¬Â¢ Integration Mgr  Ã¢â€â€š  Ã¢â€ Â Spawns children
                    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
                       Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€š
              Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
              Ã¢â€â€š           Ã¢â€â€š  Ã¢â€â€š  Ã¢â€â€š           Ã¢â€â€š
         Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â  Ã¢â€Å’Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â´Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Â
         Ã¢â€â€š zwave   Ã¢â€â€š Ã¢â€â€š   esphome   Ã¢â€â€š  Ã¢â€â€š  hue    Ã¢â€â€š
         Ã¢â€â€š (child) Ã¢â€â€š Ã¢â€â€š   (child)   Ã¢â€â€š  Ã¢â€â€š (child) Ã¢â€â€š
         Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ  Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€Ëœ
         
         Each child process:
         Ã¢â‚¬Â¢ Has its own PID
         Ã¢â‚¬Â¢ Communicates via gRPC (Unix socket) or MQTT
         Ã¢â‚¬Â¢ Has resource limits (cgroups if available)
         Ã¢â‚¬Â¢ Has its own log file
         Ã¢â‚¬Â¢ Can crash without affecting siblings or parent
         Ã¢â‚¬Â¢ Is automatically restarted by Integration Manager
```

### 3.2 Resource Consumption

#### Steady-State (typical home: 200 entities, 10 integrations)

| Resource | Expected | Alarm Threshold |
|---|---|---|
| CPU (Pi 4) | 2-5% average, <15% peak during automation burst | Sustained >50% for >5 minutes |
| RAM (core) | 15-25 MB | >100 MB |
| RAM (total with integrations) | 50-100 MB | >500 MB |
| Disk (SQLite, 10-day retention) | 100-500 MB | >2 GB |
| Disk I/O | ~5 writes/second (batched) | Sustained >100 IOPS |
| Network (local) | <1 Mbps average | N/A |
| Open file descriptors | ~200 | >1000 |

#### Scaling Characteristics

| Entity Count | RAM (Core) | RAM (Total) | Event Rate | SQLite Size (10 days) |
|---|---|---|---|---|
| 50 | 12 MB | 40 MB | ~100/min | 50 MB |
| 200 | 18 MB | 80 MB | ~500/min | 200 MB |
| 500 | 25 MB | 120 MB | ~1,500/min | 500 MB |
| 1,000 | 35 MB | 200 MB | ~3,000/min | 1 GB |
| 5,000 | 80 MB | 400 MB | ~15,000/min | 5 GB |
| 50,000 | 500 MB | 2 GB | ~150,000/min | Use TimescaleDB |

### 3.3 Logging

#### Log Levels

| Level | When Used | Example |
|---|---|---|
| `error` | Something is broken, user action may be needed | Integration crash, database write failure, authentication failure |
| `warn` | Something unexpected, but system continues | Entity unavailable, automation condition timeout, deprecated config key |
| `info` | Significant operational events | Integration started, automation triggered, config reloaded, service called |
| `debug` | Detailed operational data | State change details, MQTT message payloads, template render results |
| `trace` | Wire-level protocol data | Raw Z-Wave frames, MQTT packet dumps, HTTP request/response bodies |

#### Log Configuration

```toml
[logger]
default = "info"
file = "/var/log/marge/marge.log"
max_size = "50MB"
max_files = 5
format = "json"  # or "text"

[logger.levels]
"marge::core" = "info"
"marge::automation" = "info"
"marge::integration::zwave" = "warn"
"marge::integration::esphome" = "debug"   # Troubleshooting
"marge::recorder" = "warn"
"marge::api::http" = "info"
"marge::api::ws" = "warn"
"marge::mqtt::broker" = "warn"
```

#### Structured Log Format (JSON)

```json
{
  "ts": "2026-02-12T05:30:00.123Z",
  "level": "info",
  "target": "marge::automation",
  "msg": "Automation triggered",
  "automation_id": "morning_lights",
  "trigger_type": "sun",
  "trigger_event": "sunrise",
  "trigger_offset": "-01:00:00",
  "execution_time_us": 847
}
```

### 3.4 Health Monitoring

#### Built-in Health Endpoint

```
GET /api/health

{
  "status": "healthy",            // healthy | degraded | unhealthy
  "uptime_seconds": 432000,
  "version": "0.1.0",
  "core": {
    "state_machine": {
      "entity_count": 247,
      "events_per_minute": 523,
      "last_event_age_ms": 42
    },
    "mqtt_broker": {
      "connected_clients": 18,
      "messages_per_minute": 1247,
      "retained_messages": 312
    },
    "recorder": {
      "db_size_bytes": 214958080,
      "pending_writes": 0,
      "last_write_age_ms": 823
    },
    "automations": {
      "total": 34,
      "enabled": 31,
      "triggered_last_hour": 12
    }
  },
  "integrations": {
    "zwave": {
      "status": "running",
      "pid": 1234,
      "uptime_seconds": 431998,
      "entities": 45,
      "last_restart": null
    },
    "esphome": {
      "status": "running",
      "pid": 1235,
      "uptime_seconds": 431995,
      "entities": 82,
      "last_restart": null
    },
    "hue": {
      "status": "degraded",
      "pid": 1236,
      "uptime_seconds": 3600,
      "entities": 24,
      "last_restart": "2026-02-12T04:30:00Z",
      "restart_count": 2,
      "last_error": "Bridge connection timeout"
    }
  },
  "system": {
    "cpu_percent": 3.2,
    "memory_rss_bytes": 87031808,
    "disk_available_bytes": 28147483648,
    "load_average": [0.12, 0.08, 0.05]
  }
}
```

#### MQTT Health Topics

```
marge/system/status          Ã¢â€ â€™ "online" (retained, LWT = "offline")
marge/system/health          Ã¢â€ â€™ JSON health payload (every 60s)
marge/integration/+/status   Ã¢â€ â€™ "online"/"offline" per integration
```

#### Prometheus Metrics (Optional)

```
GET /api/metrics

# HELP marge_entities_total Total number of registered entities
# TYPE marge_entities_total gauge
marge_entities_total 247

# HELP marge_events_total Total events processed
# TYPE marge_events_total counter
marge_events_total{type="state_changed"} 1247832
marge_events_total{type="call_service"} 34521
marge_events_total{type="automation_triggered"} 8923

# HELP marge_state_change_duration_seconds State change processing time
# TYPE marge_state_change_duration_seconds histogram
marge_state_change_duration_seconds_bucket{le="0.0001"} 1198234
marge_state_change_duration_seconds_bucket{le="0.001"} 1247001

# HELP marge_automation_trigger_duration_seconds Automation trigger-to-action time
# TYPE marge_automation_trigger_duration_seconds histogram
marge_automation_trigger_duration_seconds_bucket{le="0.001"} 7823
marge_automation_trigger_duration_seconds_bucket{le="0.01"} 8901

# HELP marge_integration_status Integration health
# TYPE marge_integration_status gauge
marge_integration_status{integration="zwave",status="running"} 1
marge_integration_status{integration="hue",status="degraded"} 1

# HELP marge_recorder_db_size_bytes SQLite database size
# TYPE marge_recorder_db_size_bytes gauge
marge_recorder_db_size_bytes 214958080
```

---

## 4. FAILURE MODES & RECOVERY

### 4.1 Failure Classification

| Class | Severity | Example | Impact | Detection | Recovery |
|---|---|---|---|---|---|
| **F1: Core crash** | Critical | Rust panic, OOM kill | Total system loss | systemd watchdog, process monitor | Automatic restart via systemd (RestartSec=5). State restored from SQLite. |
| **F2: Integration crash** | Major | Z-Wave plugin segfault, Go integration panic | Single protocol loss, affected entities Ã¢â€ â€™ `unavailable` | Integration Manager heartbeat, process exit detection | Automatic restart with exponential backoff (5s, 10s, 30s, 60s, max 5min). Parent unaffected. |
| **F3: Device unreachable** | Minor | WiFi device offline, Hue bridge rebooting | Individual entity Ã¢â€ â€™ `unavailable` | Integration-specific health checks, poll timeouts | Entity marked `unavailable`. State restored when device reconnects. No system action needed. |
| **F4: Database corruption** | Major | SD card failure, power loss during write | History loss, potential state loss | SQLite integrity check on startup, WAL checksum | WAL mode protects against most corruption. Fallback: restore from last backup. Core can start with empty DB. |
| **F5: Configuration error** | Major | Invalid YAML, bad automation | Affected component fails to load | Config validation on startup and reload | System starts in Safe Mode if core config invalid. Individual automations/integrations skip with warning if their config is bad. |
| **F6: Network failure** | Moderate | WiFi down, router crash | Cloud integrations fail, WiFi devices unreachable | Periodic connectivity checks | Local devices on wired protocols (Z-Wave, Zigbee, USB) unaffected. WiFi devices reconnect automatically when network returns. |
| **F7: Disk full** | Major | Recorder fills SD card | History writes fail, potential instability | Disk space monitoring, SQLite PRAGMA checks | Recorder automatically purges oldest data. Alert fired at 90% capacity. Emergency purge at 95%. |

### 4.2 Recovery Procedures

#### F1: Core Crash Ã¢â‚¬â€ Automatic Recovery

```
TIMELINE:
  T+0s     Core process crashes (e.g., unexpected panic)
  T+0s     systemd detects process exit
  T+0.1s   Integration child processes detect parent gone
           Ã¢â€ â€™ Children gracefully shut down (or are killed after 10s)
  T+5s     systemd restarts marge (RestartSec=5)
  T+5.4s   Core binary starts, loads configuration
  T+5.5s   SQLite opened, WAL recovered, state restored
  T+5.6s   MQTT broker accepting connections
  T+5.8s   HTTP/WebSocket server listening
  T+6s     Integration Manager spawns child processes
  T+8s     Z-Wave controller reconnects, re-interviews
  T+10s    ESP/MQTT devices reconnect (their retry loop)
  T+15s    Most entities back to current state
  T+30s    All entities reporting (Z-Wave may take longest)

TOTAL OUTAGE: ~30 seconds

WHAT WAS LOST:
  - Events during the 30-second gap (not recoverable)
  - Any automation actions that were mid-execution
  - At most 5 minutes of uncommitted state history
    (SQLite commit interval default)

WHAT WAS PRESERVED:
  - All entity state as of last commit
  - All configuration
  - All automation definitions
  - Z-Wave/Zigbee network keys and topology
  - All entity/device registry metadata
```

#### F2: Integration Crash Ã¢â‚¬â€ Isolated Recovery

```
TIMELINE:
  T+0s     Z-Wave integration process crashes
  T+0s     Integration Manager detects child exit
  T+0.1s   All Z-Wave entities marked "unavailable"
  T+0.1s   state_changed events fired for each entity
  T+0.1s   Log: ERROR "Integration 'zwave' crashed (exit code 1)"
  T+0.5s   Automations that depend on Z-Wave entities:
           Ã¢â€ â€™ Triggers: will not fire (entities unavailable)
           Ã¢â€ â€™ Conditions: will evaluate unavailable
           Ã¢â€ â€™ Actions: service calls return error
  T+5s     Integration Manager restarts Z-Wave (backoff: 5s)
  T+8s     Z-Wave controller re-initialized
  T+15s    Entities begin reporting again Ã¢â€ â€™ "unavailable" clears
  T+15s    state_changed events fire Ã¢â€ â€™ automations resume

WHAT ELSE WAS AFFECTED:
  - Nothing. Zigbee, MQTT, WiFi devices all continued normally.
  - Frontend continued serving (Z-Wave devices show "unavailable").
  - Other automations continued executing.
  - MQTT broker continued operating.

BACKOFF SCHEDULE (if integration keeps crashing):
  Restart 1: 5 seconds
  Restart 2: 10 seconds
  Restart 3: 30 seconds
  Restart 4: 60 seconds
  Restart 5+: 300 seconds (5 minutes)
  After 10 restarts: marked "failed", manual intervention needed
  Ã¢â€ â€™ Log: ERROR "Integration 'zwave' failed after 10 restarts. 
          Manual restart required via UI or CLI."
```

#### F4: Database Corruption Ã¢â‚¬â€ Recovery Ladder

```
LEVEL 1: WAL Recovery (automatic)
  Ã¢â€ â€™ SQLite WAL mode protects against most power-loss corruption
  Ã¢â€ â€™ On startup, SQLite automatically replays the WAL
  Ã¢â€ â€™ No data loss beyond the last committed transaction

LEVEL 2: Integrity Check (automatic on startup)
  Ã¢â€ â€™ PRAGMA integrity_check
  Ã¢â€ â€™ If issues found: attempt PRAGMA writable_schema repair
  Ã¢â€ â€™ Log: WARN "Database integrity issues detected, attempting repair"

LEVEL 3: State-Only Recovery (automatic)
  Ã¢â€ â€™ If history tables are corrupted but registry tables intact:
  Ã¢â€ â€™ Truncate history/statistics tables
  Ã¢â€ â€™ Preserve entity_registry, device_registry, config_entries
  Ã¢â€ â€™ System starts with registries intact but no history
  Ã¢â€ â€™ Log: WARN "History data lost due to corruption. 
          Registries preserved."

LEVEL 4: Backup Restore (semi-automatic)
  Ã¢â€ â€™ If database is unrecoverable:
  Ã¢â€ â€™ Marge detects corruption Ã¢â€ â€™ enters Safe Mode
  Ã¢â€ â€™ UI presents: "Database corrupted. Restore from backup?"
  Ã¢â€ â€™ Lists available backups with dates
  Ã¢â€ â€™ User selects backup Ã¢â€ â€™ restored Ã¢â€ â€™ system restarts
  Ã¢â€ â€™ Log: ERROR "Database unrecoverable. Safe Mode entered."

LEVEL 5: Fresh Start (manual)
  Ã¢â€ â€™ If no backups available:
  Ã¢â€ â€™ Delete marge.db
  Ã¢â€ â€™ System starts fresh with configuration intact
  Ã¢â€ â€™ Entities re-discovered from integrations
  Ã¢â€ â€™ All history lost, all registries rebuilt
  Ã¢â€ â€™ The nuclear option. Config files are untouched.
```

#### F5: Configuration Error

```
SCENARIO A: Core config invalid (marge won't start)
  Ã¢â€ â€™ Config validation runs before anything else
  Ã¢â€ â€™ Validation fails Ã¢â€ â€™ Safe Mode
  Ã¢â€ â€™ Minimal HTTP server starts on port 8123
  Ã¢â€ â€™ UI shows: "Configuration error on line 47: 
      unknown key 'platfrom' (did you mean 'platform'?)"
  Ã¢â€ â€™ User fixes config via UI editor or SSH
  Ã¢â€ â€™ Click "Retry" Ã¢â€ â€™ system starts normally

SCENARIO B: Automation config invalid (system starts, auto fails)
  Ã¢â€ â€™ Core starts normally
  Ã¢â€ â€™ Automation engine loads automations one by one
  Ã¢â€ â€™ Bad automation Ã¢â€ â€™ skipped with warning
  Ã¢â€ â€™ Log: WARN "Automation 'morning_lights' failed to load: 
          invalid trigger type 'stat' (did you mean 'state'?)"
  Ã¢â€ â€™ All other automations work fine
  Ã¢â€ â€™ UI shows warning badge on Automations page

SCENARIO C: Integration config invalid
  Ã¢â€ â€™ Same as Scenario B Ã¢â‚¬â€ integration skipped, everything else works
```

### 4.3 Watchdog Architecture

```toml
# configuration.toml
[watchdog]
enabled = true
core_timeout = 30          # seconds Ã¢â‚¬â€ if core event loop stalls
integration_timeout = 60   # seconds Ã¢â‚¬â€ if integration stops responding
disk_check_interval = 300  # seconds
disk_warn_percent = 90
disk_critical_percent = 95
```

```
Watchdog checks (every 10 seconds):
  Ã¢Å“â€œ Core event loop responsive (internal heartbeat)
  Ã¢Å“â€œ MQTT broker accepting connections
  Ã¢Å“â€œ HTTP server accepting connections
  Ã¢Å“â€œ SQLite writable (test write to health table)
  Ã¢Å“â€œ Each integration responding to health check (gRPC ping)
  Ã¢Å“â€œ Disk space above threshold
  Ã¢Å“â€œ Memory usage below threshold
  Ã¢Å“â€œ File descriptor count below threshold

If core event loop stalls for >30 seconds:
  Ã¢â€ â€™ Watchdog thread (separate OS thread, not on async runtime) 
  Ã¢â€ â€™ Dumps thread/task state to log
  Ã¢â€ â€™ Triggers controlled restart
  Ã¢â€ â€™ If restart fails: process exits, systemd takes over
```

---

## 5. MAINTENANCE OPERATIONS

### 5.1 Updates

#### Update Strategy: Atomic Binary Swap

```
CURRENT STATE:
  /usr/local/bin/marge             Ã¢â€ Â running binary (v0.1.0)
  /usr/local/bin/marge.backup      Ã¢â€ Â previous version (if any)

UPDATE PROCESS:
  1. Download new binary to /tmp/marge-new
  2. Verify checksum (SHA-256)
  3. Verify signature (ed25519, Marge project key)
  4. Run: marge-new --self-test (loads config, checks DB, exits)
  5. If self-test fails Ã¢â€ â€™ abort, log error, no change
  6. Stop marge service
  7. mv marge marge.backup
  8. mv marge-new marge
  9. Start marge service
  10. Health check within 30 seconds
  11. If unhealthy Ã¢â€ â€™ automatic rollback:
      mv marge marge.failed
      mv marge.backup marge
      Start marge
      Alert: "Update to v0.2.0 failed, rolled back to v0.1.0"
```

**Total downtime: 5-10 seconds** (stop + swap + start).

For Docker deployments:

```bash
docker compose pull
docker compose up -d
# Docker handles the swap. Rollback via image tag.
```

#### Database Migrations

```
Marge uses SQLite with a versioned schema.

On startup:
  1. Read schema_version from metadata table
  2. If schema_version < current_version:
     a. Create backup: marge.db Ã¢â€ â€™ marge.db.pre-migration-backup
     b. Run migrations sequentially
     c. Update schema_version
     d. Log: INFO "Database migrated from v3 to v5"
  3. If migration fails:
     a. Restore from pre-migration backup
     b. Start with old schema (if binary is compatible)
     c. Or enter Safe Mode with error message

Migrations are:
  - Forward-only (no downgrade path in the migration itself)
  - Idempotent (safe to run twice)
  - Tested against conformance suite
  - Backup is the rollback mechanism
```

### 5.2 Backups

#### Automatic Backup Schedule

```toml
[backup]
enabled = true
directory = "/var/lib/marge/backups"
daily = true                    # Keep 7 daily backups
weekly = true                   # Keep 4 weekly backups
monthly = true                  # Keep 3 monthly backups
time = "03:00"                  # When to run daily backup
include_history = false         # History is large; exclude by default
```

#### What's Backed Up

```
ALWAYS BACKED UP (small, critical):
  Ã¢Å“â€œ /etc/marge/           (all config files, automations, scripts, secrets)
  Ã¢Å“â€œ Entity registry          (entity_id mappings, custom names)
  Ã¢Å“â€œ Device registry          (device groupings, area assignments)
  Ã¢Å“â€œ Config entries           (integration configurations)
  Ã¢Å“â€œ User accounts            (credentials, permissions)
  Ã¢Å“â€œ Z-Wave network keys      (losing these = re-interview all devices)
  Ã¢Å“â€œ Zigbee network data      (coordinator state)
  Ã¢Å“â€œ Core settings            (location, units, timezone)

OPTIONALLY BACKED UP (can be large):
  Ã¢â€”â€¹ State history            (10 days default = 100MB-1GB)
  Ã¢â€”â€¹ Statistics               (hourly/daily/monthly aggregates)
  Ã¢â€”â€¹ Automation traces        (debug data)

NEVER BACKED UP (ephemeral/regenerable):
  Ã¢Å“â€” Logs                     (rotated, not critical)
  Ã¢Å“â€” TLS certificates         (regenerated if missing)
  Ã¢Å“â€” MQTT session state       (clients reconnect)
  Ã¢Å“â€” Current entity state     (re-fetched from devices on startup)
```

#### Backup Format

```
marge-backup-2026-02-12.tar.gz
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ manifest.json               # Backup metadata, version, checksums
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ config/                     # Full /etc/marge/ tree
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ registries/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ entity_registry.json
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ device_registry.json
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ area_registry.json
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ config_entries.json          # Integration configurations
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ users.json                   # User accounts (hashed passwords)
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ integration_data/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ zwave_network.json       # Z-Wave network backup
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ zigbee_network.json      # Zigbee coordinator backup
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ history.db                   # (optional) SQLite history export
```

#### Restore

```bash
# CLI restore
marge restore /path/to/marge-backup-2026-02-12.tar.gz

# Or via UI: Settings Ã¢â€ â€™ System Ã¢â€ â€™ Backups Ã¢â€ â€™ Upload & Restore

# Restore process:
# 1. Validate backup integrity (checksums)
# 2. Stop all integrations
# 3. Restore config files
# 4. Restore registries
# 5. Restore integration data (Z-Wave keys, etc.)
# 6. Optionally restore history
# 7. Restart system
# Total time: 10-30 seconds (without history), 1-5 minutes (with history)
```

### 5.3 Configuration Management

#### Config Reload (No Restart Required)

```
THESE CAN BE RELOADED LIVE:
  Ã¢Å“â€œ Automations              Ã¢â€ â€™ POST /api/services/automation/reload
  Ã¢Å“â€œ Scripts                  Ã¢â€ â€™ POST /api/services/script/reload
  Ã¢Å“â€œ Scenes                   Ã¢â€ â€™ POST /api/services/scene/reload
  Ã¢Å“â€œ Groups                   Ã¢â€ â€™ POST /api/services/group/reload
  Ã¢Å“â€œ Input entities           Ã¢â€ â€™ POST /api/services/input_*/reload
  Ã¢Å“â€œ Template entities        Ã¢â€ â€™ POST /api/services/template/reload
  Ã¢Å“â€œ Logger levels            Ã¢â€ â€™ POST /api/services/logger/set_level
  Ã¢Å“â€œ Custom cards             Ã¢â€ â€™ Browser refresh

THESE REQUIRE RESTART:
  Ã¢Å“â€” Core config (location, units, timezone)
  Ã¢Å“â€” HTTP server config (port, TLS)
  Ã¢Å“â€” MQTT broker config
  Ã¢Å“â€” Integration additions/removals
  Ã¢Å“â€” Database config
```

#### Configuration Validation

```bash
# Validate without starting
marge check-config --config /etc/marge/

# Output:
# Ã¢Å“â€œ configuration.toml: valid
# Ã¢Å“â€œ automations.yaml: valid (34 automations)
# Ã¢Å“â€” scenes.yaml: error on line 23:
#     entity_id "light.livng_room" does not match any known entity
#     (did you mean "light.living_room"?)
# Ã¢Å“â€œ scripts.yaml: valid (8 scripts)
# 
# Result: 1 error, 0 warnings
```

---

## 6. HA-LEGACY MIGRATION

### 6.1 Migration Path

```
PRE-MIGRATION:
  1. Run HA backup from HA UI (Settings Ã¢â€ â€™ System Ã¢â€ â€™ Backups)
  2. Download backup .tar file
  3. Note HA version (migration tested against specific versions)
  
MIGRATION:
  4. Install Marge (Method 1 or 2 from Ã‚Â§2.2)
  5. Run migration wizard:
     marge migrate --from-ha-backup /path/to/ha-backup.tar
  
  The wizard:
  a. Extracts HA backup
  b. Converts configuration.yaml Ã¢â€ â€™ configuration.toml (native)
     AND preserves configuration.yaml (compatibility mode)
  c. Copies automations.yaml, scripts.yaml, scenes.yaml as-is
  d. Imports entity registry (preserves entity_id mappings)
  e. Imports device registry (preserves device names, areas)
  f. Imports user accounts (re-hashes passwords for Marge auth)
  g. Imports Z-Wave network backup (if applicable)
  h. Generates compatibility report:
     - Supported integrations: listed with Ã¢Å“â€œ
     - Unsupported integrations: listed with Ã¢Å“â€” and alternatives
     - Automations: validated, warnings for unsupported features
  
POST-MIGRATION:
  6. Start Marge
  7. Run conformance spot-check:
     marge verify --quick
     (Tests 50 core behaviors to confirm system is working)
  8. Verify dashboards render correctly
  9. Verify automations trigger correctly (check traces)
  10. Run parallel with HA for 1 week (recommended)
      - Both systems read-only on devices
      - Compare state/event behavior
      - Cut over when confident
```

### 6.2 What Migrates Automatically

| Component | Migration Support | Notes |
|---|---|---|
| Core config (location, units, timezone) | Ã¢Å“â€¦ Full | YAML Ã¢â€ â€™ TOML conversion |
| Automations | Ã¢Å“â€¦ Full | YAML preserved as-is |
| Scripts | Ã¢Å“â€¦ Full | YAML preserved as-is |
| Scenes | Ã¢Å“â€¦ Full | YAML preserved as-is |
| Input entities | Ã¢Å“â€¦ Full | YAML preserved as-is |
| Entity registry | Ã¢Å“â€¦ Full | JSON import |
| Device registry | Ã¢Å“â€¦ Full | JSON import |
| Area registry | Ã¢Å“â€¦ Full | JSON import |
| User accounts | Ã¢Å“â€¦ Full | Password re-hash |
| Dashboards (Lovelace) | Ã°Å¸Å¸Â¡ Partial | Card definitions preserved; custom cards may need equivalents |
| MQTT configuration | Ã¢Å“â€¦ Full | Direct mapping |
| Z-Wave network | Ã¢Å“â€¦ Full | NVM backup import |
| Zigbee network | Ã°Å¸Å¸Â¡ Partial | Coordinator backup; may need re-pair for some devices |
| History data | Ã°Å¸Å¸Â¡ Optional | Large import; offered but not required |
| Custom integrations (HACS) | Ã¢ÂÅ’ Manual | Need Marge equivalents or compatibility shim |
| Add-ons | Ã¢ÂÅ’ N/A | Marge doesn't use the add-on model. Equivalent functionality via Docker Compose sidecar services. |

### 6.3 Running HA and Marge in Parallel

For risk-averse migration:

```yaml
# docker-compose.parallel.yml
# Run both HA and Marge simultaneously for comparison

services:
  ha-legacy:
    image: ghcr.io/home-assistant/home-assistant:2024.12
    ports:
      - "8124:8123"   # HA on port 8124
    volumes:
      - ./ha-config:/config
    # READ-ONLY: Don't let HA control devices during parallel run
    # (Or use a separate Z-Wave stick / separate MQTT prefix)

  marge:
    image: ghcr.io/marge-home/marge:latest
    ports:
      - "8123:8123"   # Marge on standard port
    volumes:
      - ./marge-config:/etc/marge
      - ./marge-data:/var/lib/marge
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0

  # Compare state between the two systems
  comparator:
    image: ghcr.io/marge-home/migration-comparator:latest
    environment:
      HA_URL: http://ha-legacy:8123
      MARGE_URL: http://marge:8123
      HA_TOKEN: ${HA_TOKEN}
      MARGE_TOKEN: ${MARGE_TOKEN}
    # Generates daily report: state differences, timing differences,
    # automation behavior differences
```

---

## 7. SECURITY OPERATIONS

### 7.1 Authentication

```
AUTHENTICATION METHODS:
  1. Local accounts (username + bcrypt-hashed password)
  2. Long-lived access tokens (for API/scripts)
  3. OAuth 2.0 (for third-party integrations)
  4. Trusted networks (optional Ã¢â‚¬â€ skip auth for local subnet)
  5. MFA via TOTP (optional, recommended for remote access)

SESSION MANAGEMENT:
  - Web UI: JWT tokens with 30-minute expiry, refresh via cookie
  - API: Bearer tokens (long-lived, no expiry, revocable)
  - WebSocket: Authenticated per-connection, no re-auth needed
```

### 7.2 Network Security

```
DEFAULT (out of the box):
  - HTTP on port 8123 (no TLS) Ã¢â‚¬â€ local network only
  - MQTT on port 1883 (no TLS) Ã¢â‚¬â€ local network only
  - No ports exposed to internet
  - mDNS/SSDP for local discovery

HARDENED (recommended for remote access):
  - TLS on all ports (auto-generated self-signed or Let's Encrypt)
  - MQTT with TLS + client certificates for integrations
  - Reverse proxy (nginx/Caddy) for HTTPS termination
  - Trusted networks restricted to local subnet
  - Rate limiting on auth endpoints
  - Fail2ban-compatible log format for brute-force protection
```

### 7.3 Integration Sandboxing

```
ISOLATION MODEL:
  Each integration runs as a separate process with:
  
  FILESYSTEM:
    - Read access: own config directory
    - Write access: own data directory (/var/lib/marge/integrations/{name}/)
    - No access to: core config, other integrations, system files
  
  NETWORK:
    - Localhost: gRPC to core (Unix socket preferred)
    - MQTT: Scoped topics (marge/integration/{name}/# only)
    - Outbound: Unrestricted (for cloud integrations)
    - Inbound: None (core connects to integration, not vice versa)
  
  RESOURCES (if cgroups available):
    - Memory limit: 256MB default (configurable per integration)
    - CPU: No hard limit, but OOM priority lower than core
    - File descriptors: 256 default
  
  PRIVILEGES:
    - No root access
    - No capability escalation
    - Device access (USB) only for integrations that need it
      (Z-Wave, Zigbee Ã¢â‚¬â€ explicitly configured)
```

### 7.4 Secrets Management

```toml
# secrets.yaml (encrypted at rest via age/SOPS)
mqtt_password: "hunter2"
hue_api_key: "abcdef123456"
latitude: "40.3916"   # Some people consider location sensitive

# Reference in configuration:
# configuration.toml
[mqtt]
password = "!secret mqtt_password"

# Or in YAML (HA-compatible):
mqtt:
  password: !secret mqtt_password
```

```
ENCRYPTION AT REST:
  - secrets.yaml encrypted with age (https://age-encryption.org)
  - Key stored in /var/lib/marge/.marge-key
  - Key file permissions: 0600, owned by marge user
  - On first run: key auto-generated
  - For backup: key must be backed up separately 
    (or user provides passphrase-based encryption)
```

---

## 8. CLI REFERENCE

```
marge                        # Start the server (foreground)
marge --config /path/to/dir  # Specify config directory
marge --safe-mode            # Start in Safe Mode (empty config)

marge check-config           # Validate configuration files
marge migrate                # HA Ã¢â€ â€™ Marge migration wizard
marge restore                # Restore from backup
marge backup                 # Create manual backup

marge verify                 # Run quick self-test (50 core behaviors)
marge verify --full          # Run full conformance suite

marge info                   # Show system info (version, paths, entities)
marge logs                   # Tail the log file
marge logs --integration zwave  # Tail integration-specific log

marge integration list       # List all integrations and their status
marge integration restart zwave # Restart a specific integration
marge integration logs zwave    # View integration log

marge entity list            # List all entities
marge entity get light.kitchen  # Show entity state
marge entity call light.turn_on light.kitchen brightness=128

marge install-service        # Install systemd service file
marge version                # Print version and build info
```

---

## 9. OPERATIONAL CHECKLISTS

### 9.1 Pre-Deployment Checklist

```
Ã¢â€“Â¡ Hardware selected and tested (see Ã‚Â§2.1)
Ã¢â€“Â¡ OS installed and updated
Ã¢â€“Â¡ Static IP assigned (or DHCP reservation)
Ã¢â€“Â¡ USB devices connected (Z-Wave, Zigbee)
Ã¢â€“Â¡ Time zone configured correctly
Ã¢â€“Â¡ NTP synchronization verified
Ã¢â€“Â¡ If using SD card: read-only root filesystem considered
Ã¢â€“Â¡ If using SSD: TRIM enabled
Ã¢â€“Â¡ UPS connected (recommended for security-critical deployments)
```

### 9.2 Post-Install Verification

```
Ã¢â€“Â¡ Web UI accessible at http://<host>:8123
Ã¢â€“Â¡ Admin account created and working
Ã¢â€“Â¡ Location/timezone correct in Settings
Ã¢â€“Â¡ USB devices detected (Settings Ã¢â€ â€™ System Ã¢â€ â€™ Hardware)
Ã¢â€“Â¡ MQTT broker running (check /api/health)
Ã¢â€“Â¡ At least one integration added and showing entities
Ã¢â€“Â¡ Create test automation Ã¢â€ â€™ verify it triggers
Ã¢â€“Â¡ Verify history graph shows data
Ã¢â€“Â¡ Run: marge verify
Ã¢â€“Â¡ Configure automatic backups
```

### 9.3 Monthly Maintenance

```
Ã¢â€“Â¡ Check /api/health Ã¢â‚¬â€ all green?
Ã¢â€“Â¡ Review logs for recurring warnings
Ã¢â€“Â¡ Verify backups are running (check backup directory)
Ã¢â€“Â¡ Check disk usage (df -h /var/lib/marge)
Ã¢â€“Â¡ Review integration restart counts (any repeatedly crashing?)
Ã¢â€“Â¡ Update Marge if new version available
Ã¢â€“Â¡ Test restore from backup (on separate hardware, annually)
```

### 9.4 Incident Response

```
SYMPTOM: "Nothing is responding"
  1. SSH into host
  2. systemctl status marge
  3. If not running: journalctl -u marge --since "10 minutes ago"
  4. Look for OOM kill, disk full, or crash
  5. systemctl restart marge
  6. Check /api/health within 30 seconds

SYMPTOM: "One protocol is down" (e.g., Z-Wave devices unavailable)
  1. marge integration list
  2. marge integration logs zwave
  3. marge integration restart zwave
  4. If repeated: check USB device (ls /dev/ttyUSB*)
  5. If USB missing: unplug/replug, or check dmesg

SYMPTOM: "Automations aren't firing"
  1. Check automation is enabled: GET /api/states/automation.{name}
  2. Check traces: Settings Ã¢â€ â€™ Automations Ã¢â€ â€™ (automation) Ã¢â€ â€™ Traces
  3. Check entity states that automation depends on
  4. Check condition evaluation in trace
  5. Check log for template errors

SYMPTOM: "System is slow"
  1. Check /api/health Ã¢â€ â€™ system.cpu_percent, system.memory_rss_bytes
  2. Check event rate: is something spamming state changes?
  3. Check integration resource usage: top, htop
  4. Check disk I/O: iostat (SD card dying?)
  5. Check SQLite size: ls -la /var/lib/marge/marge.db

SYMPTOM: "I locked myself out"
  1. SSH into host
  2. marge --safe-mode (starts with no auth required on localhost)
  3. Access http://localhost:8123, reset password
  4. Restart normally: systemctl restart marge
```

---

## 10. CAPACITY PLANNING

### 10.1 Sizing Guide

| Home Size | Entities | Integrations | Recommended Hardware | RAM | Storage |
|---|---|---|---|---|---|
| **Apartment** (studio-2BR) | 20-50 | 2-3 | Pi 4 (2GB) | 512 MB enough | 16 GB SD |
| **Small house** (2-3BR) | 50-200 | 3-5 | Pi 4 (4GB) | 1 GB enough | 32 GB SSD |
| **Medium house** (3-4BR) | 200-500 | 5-10 | Pi 5 (8GB) or Mini PC | 2 GB comfortable | 64 GB SSD |
| **Large house** (5+BR) | 500-1,000 | 10-15 | Mini PC / NUC | 4 GB recommended | 128 GB SSD |
| **Estate / Light commercial** | 1,000-5,000 | 15+ | NUC / small server | 8 GB | 256 GB SSD |
| **MDU / Commercial** | 5,000+ | 20+ | Server with TimescaleDB | 16 GB+ | NVMe SSD |

### 10.2 When to Scale Up

```
YOU NEED MORE RAM WHEN:
  - /api/health shows memory > 80% of available
  - OOM kills in dmesg
  - Integration restarts correlate with high memory

YOU NEED MORE DISK WHEN:
  - Recorder purge can't keep up with ingest rate
  - SQLite WAL file grows > 100MB
  - Disk usage alerts firing

YOU NEED MORE CPU WHEN:
  - Automation trigger-to-action latency > 100ms
  - Template rendering timeout warnings
  - API response latency > 50ms

YOU NEED TIMESCALEDB WHEN:
  - SQLite > 5GB even with 10-day retention
  - Long-term statistics queries are slow
  - You want months/years of history
  - You want Grafana dashboards with complex queries
```

---

**END OF DOCUMENT**

*"Theory of Operations: the document that answers every question* 
*someone asks at 2 AM when the system is down and you're in your underwear."*
