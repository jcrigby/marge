#!/bin/bash
# run-demo.sh — Run the Marge Innovation Week demo
#
# Usage:
#   ./scripts/run-demo.sh                    # Full stack (HA + Marge standalone + dashboard)
#   ./scripts/run-demo.sh docker             # Full stack (all containers via docker compose)
#   ./scripts/run-demo.sh marge-only         # Just Marge (no Docker)
#   ./scripts/run-demo.sh scenario [chapter] # Run scenario driver
#   ./scripts/run-demo.sh highlight          # 15-min highlight reel (standalone Marge)
#   ./scripts/run-demo.sh docker-highlight   # 15-min highlight reel (Docker Marge)
#
# Prerequisites:
#   - Docker and docker compose (for full stack)
#   - Rust toolchain (for building Marge)
#   - Python 3 with httpx, paho-mqtt, websockets, pytest (pip install -r tests/requirements.txt)

set -euo pipefail
cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

refresh_ha_token() {
  if curl -sf http://localhost:8123/api/ > /dev/null 2>&1; then
    bash scripts/ha-refresh-token.sh 2>/dev/null && return 0
  fi
  return 1
}

case "${1:-full}" in
  full|start)
    echo -e "${BOLD}=== Marge Demo — Full Stack ===${NC}"
    echo ""

    # Build Marge
    echo -e "${BLUE}Building Marge...${NC}"
    (cd marge-core && cargo build --release 2>&1 | tail -1)
    echo -e "${GREEN}Binary: $(ls -lh marge-core/target/release/marge | awk '{print $5}')${NC}"
    echo ""

    # Start Docker services
    echo -e "${BLUE}Starting Docker services (mosquitto + HA)...${NC}"
    docker compose up -d mosquitto ha-legacy 2>&1 | tail -2
    echo ""

    # Start Marge
    echo -e "${BLUE}Starting Marge...${NC}"
    pkill -9 marge 2>/dev/null || true
    sleep 0.5
    MARGE_AUTOMATIONS_PATH=./ha-config/automations.yaml \
    MARGE_SCENES_PATH=./ha-config/scenes.yaml \
    MARGE_MQTT_PORT=1884 \
    RUST_LOG=info \
      ./marge-core/target/release/marge &
    MARGE_PID=$!
    sleep 2

    # Check HA onboarding
    if curl -sf http://localhost:8123/api/onboarding 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if any(not s['done'] for s in d) else 1)" 2>/dev/null; then
      echo -e "${BLUE}Running HA onboarding...${NC}"
      bash scripts/ha-onboard.sh 2>&1 | tail -5
    fi

    echo ""
    echo -e "${BOLD}=== Services Running ===${NC}"
    echo -e "  HA:         http://localhost:8123"
    echo -e "  Marge:      http://localhost:8124"
    echo -e "  Marge MQTT: localhost:1884"
    echo -e "  Dashboard:  Open dashboard/index.html in a browser"
    echo ""
    echo -e "  Marge PID:  $MARGE_PID"
    echo -e "  Health:     curl http://localhost:8124/api/health"
    echo ""
    echo -e "${BLUE}To run scenario:${NC}"
    echo "  ./scripts/run-demo.sh scenario dawn"
    echo "  ./scripts/run-demo.sh scenario         # all chapters"
    echo ""
    echo -e "${BLUE}To run CTS:${NC}"
    echo "  SUT_URL=http://localhost:8124 SUT_WS_URL=ws://localhost:8124/api/websocket SUT_TOKEN=test-token python3 -m pytest tests/ -v"
    ;;

  docker)
    echo -e "${BOLD}=== Marge Demo — Full Docker Stack ===${NC}"
    echo ""

    # Build all images
    echo -e "${BLUE}Building Docker images...${NC}"
    docker compose build 2>&1 | grep -E "Built|Building" | head -10
    echo ""

    # Start everything
    echo -e "${BLUE}Starting all services...${NC}"
    docker compose up -d mosquitto ha-legacy marge dashboard 2>&1 | tail -5
    sleep 3

    # Check HA onboarding
    if curl -sf http://localhost:8123/api/onboarding 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if any(not s['done'] for s in d) else 1)" 2>/dev/null; then
      echo -e "${BLUE}Running HA onboarding...${NC}"
      bash scripts/ha-onboard.sh 2>&1 | tail -5
    fi

    echo ""
    echo -e "${BOLD}=== All Services Running ===${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep marge-demo
    echo ""
    echo -e "  Dashboard:  ${GREEN}http://localhost:3000${NC}"
    echo -e "  HA:         http://localhost:8123"
    echo -e "  Marge:      http://localhost:8124"
    echo ""
    echo -e "${BLUE}To run highlight reel:${NC}"
    echo "  ./scripts/run-demo.sh docker-highlight"
    ;;

  docker-highlight)
    echo -e "${BOLD}=== Highlight Reel — Docker Mode (15 min at 10x) ===${NC}"
    echo -e "Chapters: dawn → morning → sunset → goodnight → outage"
    echo ""

    refresh_ha_token || true
    HA_TOKEN=""
    if [ -f ha-config/.ha_token ]; then
      HA_TOKEN=$(cat ha-config/.ha_token)
    fi

    # Reset verify scores for clean run
    curl -sf -X POST http://localhost:8124/api/states/sensor.verify_ha \
      -H 'Content-Type: application/json' \
      -d '{"state":"0/0","attributes":{"ok":0,"fail":0,"total":0}}' > /dev/null 2>&1 || true
    curl -sf -X POST http://localhost:8124/api/states/sensor.verify_marge \
      -H 'Content-Type: application/json' \
      -d '{"state":"0/0","attributes":{"ok":0,"fail":0,"total":0}}' > /dev/null 2>&1 || true

    for ch in dawn morning sunset goodnight outage; do
      echo -e "\n${BLUE}>>> Chapter: ${ch}${NC}"
      env TARGET=both \
        HA_URL=http://localhost:8123 \
        HA_TOKEN="$HA_TOKEN" \
        HA_MQTT_HOST=localhost \
        HA_MQTT_PORT=1883 \
        MARGE_URL=http://localhost:8124 \
        MARGE_MQTT_HOST=localhost \
        MARGE_MQTT_PORT=1884 \
        HA_STOP_CMD="docker stop marge-demo-ha" \
        HA_START_CMD="docker start marge-demo-ha" \
        MARGE_STOP_CMD="docker stop marge-demo-marge" \
        MARGE_START_CMD="docker start marge-demo-marge" \
        SPEED="${SPEED:-10}" \
        CHAPTER="$ch" \
        python3 scenario-driver/driver.py
    done

    echo -e "\n${GREEN}=== Highlight Reel Complete ===${NC}"
    echo -e "Press S in dashboard for score card"
    ;;

  marge-only)
    echo -e "${BOLD}=== Marge — Standalone ===${NC}"
    pkill -9 marge 2>/dev/null || true
    sleep 0.5

    (cd marge-core && cargo build --release 2>&1 | tail -1)

    MARGE_AUTOMATIONS_PATH=./ha-config/automations.yaml \
    MARGE_SCENES_PATH=./ha-config/scenes.yaml \
    MARGE_MQTT_PORT=1884 \
    RUST_LOG=info \
      ./marge-core/target/release/marge &

    sleep 2
    echo -e "${GREEN}Marge running on http://localhost:8124${NC}"
    echo -e "Health: $(curl -s http://localhost:8124/api/health)"
    ;;

  scenario)
    CHAPTER="${2:-}"
    refresh_ha_token || true
    HA_TOKEN=""
    if [ -f ha-config/.ha_token ]; then
      HA_TOKEN=$(cat ha-config/.ha_token)
    fi

    CHAPTER_ENV=""
    if [ -n "$CHAPTER" ]; then
      CHAPTER_ENV="CHAPTER=$CHAPTER"
    fi

    echo -e "${BOLD}=== Running Scenario ===${NC}"
    echo -e "Chapter: ${CHAPTER:-all}"

    # Marge start command for outage recovery
    MARGE_BIN="$(pwd)/marge-core/target/release/marge"
    MARGE_START="MARGE_AUTOMATIONS_PATH=$(pwd)/ha-config/automations.yaml MARGE_SCENES_PATH=$(pwd)/ha-config/scenes.yaml MARGE_MQTT_PORT=1884 RUST_LOG=info $MARGE_BIN &"

    env TARGET=both \
      HA_URL=http://localhost:8123 \
      HA_TOKEN="$HA_TOKEN" \
      HA_MQTT_HOST=localhost \
      HA_MQTT_PORT=1883 \
      MARGE_URL=http://localhost:8124 \
      MARGE_MQTT_HOST=localhost \
      MARGE_MQTT_PORT=1884 \
      MARGE_START_CMD="$MARGE_START" \
      SPEED="${SPEED:-10}" \
      ${CHAPTER_ENV} \
      python3 scenario-driver/driver.py
    ;;

  highlight)
    echo -e "${BOLD}=== Highlight Reel (15 min at 10x) ===${NC}"
    echo -e "Chapters: dawn → morning → sunset → goodnight → outage"
    echo ""

    refresh_ha_token || true
    HA_TOKEN=""
    if [ -f ha-config/.ha_token ]; then
      HA_TOKEN=$(cat ha-config/.ha_token)
    fi

    MARGE_BIN="$(pwd)/marge-core/target/release/marge"
    MARGE_START="MARGE_AUTOMATIONS_PATH=$(pwd)/ha-config/automations.yaml MARGE_SCENES_PATH=$(pwd)/ha-config/scenes.yaml MARGE_MQTT_PORT=1884 RUST_LOG=info $MARGE_BIN &"

    # Reset verify scores for clean run
    curl -sf -X POST http://localhost:8124/api/states/sensor.verify_ha \
      -H 'Content-Type: application/json' \
      -d '{"state":"0/0","attributes":{"ok":0,"fail":0,"total":0}}' > /dev/null 2>&1 || true
    curl -sf -X POST http://localhost:8124/api/states/sensor.verify_marge \
      -H 'Content-Type: application/json' \
      -d '{"state":"0/0","attributes":{"ok":0,"fail":0,"total":0}}' > /dev/null 2>&1 || true

    for ch in dawn morning sunset goodnight outage; do
      echo -e "\n${BLUE}>>> Chapter: ${ch}${NC}"
      env TARGET=both \
        HA_URL=http://localhost:8123 \
        HA_TOKEN="$HA_TOKEN" \
        HA_MQTT_HOST=localhost \
        HA_MQTT_PORT=1883 \
        MARGE_URL=http://localhost:8124 \
        MARGE_MQTT_HOST=localhost \
        MARGE_MQTT_PORT=1884 \
        MARGE_START_CMD="$MARGE_START" \
        SPEED="${SPEED:-10}" \
        CHAPTER="$ch" \
        python3 scenario-driver/driver.py
    done

    echo -e "\n${GREEN}=== Highlight Reel Complete ===${NC}"
    echo -e "Press S in dashboard for score card"
    ;;

  cts)
    echo -e "${BOLD}=== Running CTS ===${NC}"
    SUT_URL=http://localhost:8124 \
    SUT_WS_URL=ws://localhost:8124/api/websocket \
    SUT_TOKEN=test-token \
      python3 -m pytest tests/ -v "${@:2}"
    ;;

  stop)
    echo "Stopping services..."
    pkill -9 marge 2>/dev/null || true
    docker compose down 2>/dev/null || true
    echo "Done."
    ;;

  *)
    echo "Usage: $0 {start|full|docker|marge-only|scenario [chapter]|highlight|docker-highlight|cts|stop}"
    exit 1
    ;;
esac
