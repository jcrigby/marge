#!/bin/bash
# ha-refresh-token.sh — Refresh HA access token
# Usage: ./scripts/ha-refresh-token.sh [ha_url]
# Writes fresh token to ha-config/.ha_token

set -euo pipefail

HA_URL="${1:-http://localhost:8123}"
CLIENT_ID="${HA_URL}/"
TOKEN_FILE="./ha-config/.ha_token"

# Start login flow
FLOW_ID=$(curl -sf -X POST "${HA_URL}/auth/login_flow" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${CLIENT_ID}\",\"handler\":[\"homeassistant\",null],\"redirect_uri\":\"${CLIENT_ID}\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['flow_id'])")

# Submit credentials
AUTH_CODE=$(curl -sf -X POST "${HA_URL}/auth/login_flow/${FLOW_ID}" \
    -H "Content-Type: application/json" \
    -d '{"username":"demo","password":"demo1234","client_id":"'"${CLIENT_ID}"'"}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result'])")

# Exchange for access token
ACCESS_TOKEN=$(curl -sf -X POST "${HA_URL}/auth/token" \
    -d "grant_type=authorization_code&code=${AUTH_CODE}&client_id=${CLIENT_ID}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "$ACCESS_TOKEN" > "$TOKEN_FILE"
echo "Token refreshed → $TOKEN_FILE"
