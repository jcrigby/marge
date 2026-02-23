#!/bin/bash
# pi-deploy.sh — Build ARM64 images and deploy Marge demo to Raspberry Pi
#
# Usage: ./scripts/pi-deploy.sh PI_HOST
#   PI_HOST = SSH target, e.g. "pi@raspberrypi.local" or "pi@192.168.1.100"
#
# Prerequisites:
#   - docker buildx (for ARM64 cross-compilation)
#   - SSH key auth to PI_HOST
#   - Pi has Docker + docker compose installed

set -euo pipefail
cd "$(dirname "$0")/.."

PI_HOST="${1:?Usage: $0 PI_HOST (e.g. pi@raspberrypi.local)}"
TARBALL="/tmp/marge-pi.tar.gz"
PI_DIR="~/marge-demo"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}=== Marge Pi Deployment ===${NC}"
echo -e "Target: ${BLUE}${PI_HOST}${NC}"
echo ""

# ── Step 1: Build ARM64 image ────────────────────
echo -e "${BLUE}[1/6] Building ARM64 image (this takes 30-60 min under QEMU)...${NC}"
docker buildx build \
  --platform linux/arm64 \
  -f marge-core/Dockerfile \
  -t marge:pi \
  --load \
  .
echo -e "${GREEN}  Image built: $(docker image inspect marge:pi --format '{{.Size}}' | numfmt --to=iec)${NC}"

# ── Step 2: Save + compress ──────────────────────
echo -e "${BLUE}[2/6] Saving image to ${TARBALL}...${NC}"
docker save marge:pi | gzip > "${TARBALL}"
echo -e "${GREEN}  Tarball: $(ls -lh ${TARBALL} | awk '{print $5}')${NC}"

# ── Step 3: Transfer to Pi ───────────────────────
echo -e "${BLUE}[3/6] Transferring image to Pi...${NC}"
scp "${TARBALL}" "${PI_HOST}:/tmp/marge-pi.tar.gz"
ssh "${PI_HOST}" "docker load < /tmp/marge-pi.tar.gz && rm /tmp/marge-pi.tar.gz"
echo -e "${GREEN}  Image loaded on Pi${NC}"

# ── Step 4: Rsync config files ───────────────────
echo -e "${BLUE}[4/6] Syncing config files to Pi...${NC}"
ssh "${PI_HOST}" "mkdir -p ${PI_DIR}"
rsync -avz --delete \
  ha-config \
  mosquitto \
  virtual-devices \
  docker-compose.pi-marge.yml \
  docker-compose.pi-ha.yml \
  "${PI_HOST}:${PI_DIR}/"
echo -e "${GREEN}  Files synced${NC}"

# ── Step 5: Build simulator images on Pi ─────────
echo -e "${BLUE}[5/6] Building virtual device simulators on Pi...${NC}"
ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose -f docker-compose.pi-marge.yml build"
echo -e "${GREEN}  Simulators built${NC}"

# ── Step 6: Smoke test ───────────────────────────
echo -e "${BLUE}[6/6] Smoke testing...${NC}"

# Test Marge stack
echo -e "  Starting Marge stack..."
ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose -f docker-compose.pi-marge.yml up -d"
sleep 10

PI_IP=$(echo "${PI_HOST}" | sed 's/.*@//')
if curl -sf "http://${PI_IP}:8124/api/health" > /dev/null 2>&1; then
  echo -e "${GREEN}  Marge health check: OK${NC}"
else
  echo -e "${RED}  Marge health check: FAILED (may need more startup time)${NC}"
fi

ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose -f docker-compose.pi-marge.yml down"

# Test HA stack
echo -e "  Starting HA stack..."
ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose -f docker-compose.pi-ha.yml up -d"
sleep 30  # HA takes longer to start

if curl -sf "http://${PI_IP}:8123/api/" > /dev/null 2>&1; then
  echo -e "${GREEN}  HA API check: OK${NC}"
else
  echo -e "${RED}  HA API check: FAILED (may need onboarding first)${NC}"
fi

ssh "${PI_HOST}" "cd ${PI_DIR} && docker compose -f docker-compose.pi-ha.yml down"

# Cleanup local tarball
rm -f "${TARBALL}"

echo ""
echo -e "${GREEN}${BOLD}=== Deployment Complete ===${NC}"
echo ""
echo -e "To run Marge on the Pi:"
echo -e "  ssh ${PI_HOST}"
echo -e "  cd ${PI_DIR}"
echo -e "  docker compose -f docker-compose.pi-marge.yml up -d"
echo ""
echo -e "To run HA on the Pi:"
echo -e "  ssh ${PI_HOST}"
echo -e "  cd ${PI_DIR}"
echo -e "  docker compose -f docker-compose.pi-ha.yml up -d"
echo ""
echo -e "Dashboard URL (from desktop):"
echo -e "  Marge: http://localhost:3000?marge_ws=ws://${PI_IP}:8124/api/websocket&marge_rest=http://${PI_IP}:8124/api&mode=marge-only&label=Raspberry+Pi+5"
echo -e "  HA:    http://localhost:3000?ha_ws=ws://${PI_IP}:8123/api/websocket&ha_rest=http://${PI_IP}:8123/api&mode=ha-only&label=Raspberry+Pi+5+(HA)"
