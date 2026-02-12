#!/bin/bash
# run-demo.sh — Run the Marge Innovation Week demo
#
# Usage:
#   ./scripts/run-demo.sh                    # Full stack (HA + Marge + dashboard)
#   ./scripts/run-demo.sh marge-only         # Just Marge (no Docker)
#   ./scripts/run-demo.sh scenario [chapter] # Run scenario driver
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
    echo "Usage: $0 {start|full|marge-only|scenario [chapter]|cts|stop}"
    exit 1
    ;;
esac
