#!/bin/bash
# ha-onboard.sh — Complete HA onboarding + MQTT setup via API
#
# Usage: ./scripts/ha-onboard.sh [ha_url]
# Default: http://localhost:8123
#
# This script:
#   1. Waits for HA to be ready
#   2. Completes onboarding (creates owner account)
#   3. Configures MQTT integration to connect to Mosquitto
#   4. Writes access token to ha-config/.ha_token
#
# Run ONCE after first docker compose up. Subsequent starts use
# the persisted .storage/ directory.

set -euo pipefail

HA_URL="${1:-http://localhost:8123}"
CLIENT_ID="${HA_URL}/"
TOKEN_FILE="./ha-config/.ha_token"

echo "=== Marge Demo — HA Onboarding ==="
echo "HA URL: $HA_URL"

# ── 1. Wait for HA to be ready ────────────────────────────
echo -n "Waiting for HA to start..."
until curl -sf "${HA_URL}/api/onboarding" -o /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo " ready."

# Check if onboarding is already complete
ONBOARDING=$(curl -sf "${HA_URL}/api/onboarding" 2>/dev/null || echo "[]")
if echo "$ONBOARDING" | jq -e 'length == 0' > /dev/null 2>&1; then
    echo "Onboarding already complete."
    if [ -f "$TOKEN_FILE" ]; then
        echo "Token file exists at $TOKEN_FILE"
        exit 0
    else
        echo "WARNING: No token file found. You may need to create one manually."
        exit 1
    fi
fi

# ── 2. Create owner account ──────────────────────────────
echo "Creating owner account..."
RESULT=$(curl -sf -X POST "${HA_URL}/api/onboarding/users" \
    -H "Content-Type: application/json" \
    -d "{
        \"client_id\": \"${CLIENT_ID}\",
        \"name\": \"Demo\",
        \"username\": \"demo\",
        \"password\": \"demo1234\",
        \"language\": \"en\"
    }")

AUTH_CODE=$(echo "$RESULT" | jq -r '.auth_code')
if [ -z "$AUTH_CODE" ] || [ "$AUTH_CODE" = "null" ]; then
    echo "ERROR: Failed to create owner account"
    echo "Response: $RESULT"
    exit 1
fi
echo "Owner account created."

# ── 3. Exchange auth_code for tokens ─────────────────────
echo "Exchanging auth code for tokens..."
TOKENS=$(curl -sf -X POST "${HA_URL}/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=authorization_code&code=${AUTH_CODE}&client_id=${CLIENT_ID}")

ACCESS_TOKEN=$(echo "$TOKENS" | jq -r '.access_token')
if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "ERROR: Failed to get access token"
    echo "Response: $TOKENS"
    exit 1
fi
echo "Access token obtained."

# ── 4. Complete remaining onboarding steps ───────────────
echo "Completing core config..."
curl -sf -X POST "${HA_URL}/api/onboarding/core_config" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}' > /dev/null

echo "Completing analytics..."
curl -sf -X POST "${HA_URL}/api/onboarding/analytics" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}' > /dev/null

echo "Completing integration step..."
curl -sf -X POST "${HA_URL}/api/onboarding/integration" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"client_id\": \"${CLIENT_ID}\",
        \"redirect_uri\": \"${HA_URL}/\"
    }" > /dev/null

echo "Onboarding complete."

# ── 5. Configure MQTT integration ────────────────────────
echo "Starting MQTT integration config flow..."
FLOW_RESULT=$(curl -sf -X POST "${HA_URL}/api/config/config_entries/flow" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"handler": "mqtt", "show_advanced_options": false}')

FLOW_ID=$(echo "$FLOW_RESULT" | jq -r '.flow_id')
if [ -z "$FLOW_ID" ] || [ "$FLOW_ID" = "null" ]; then
    echo "ERROR: Failed to start MQTT config flow"
    echo "Response: $FLOW_RESULT"
    exit 1
fi

echo "Submitting MQTT broker config (flow_id: $FLOW_ID)..."
MQTT_RESULT=$(curl -sf -X POST "${HA_URL}/api/config/config_entries/flow/${FLOW_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "broker": "mosquitto",
        "port": 1883,
        "username": "",
        "password": ""
    }')

MQTT_TYPE=$(echo "$MQTT_RESULT" | jq -r '.type')
if [ "$MQTT_TYPE" = "create_entry" ]; then
    echo "MQTT integration configured successfully."
elif [ "$MQTT_TYPE" = "abort" ]; then
    REASON=$(echo "$MQTT_RESULT" | jq -r '.reason')
    if [ "$REASON" = "already_configured" ]; then
        echo "MQTT integration already configured."
    else
        echo "WARNING: MQTT flow aborted: $REASON"
    fi
else
    echo "WARNING: Unexpected MQTT flow result type: $MQTT_TYPE"
    echo "Response: $MQTT_RESULT"
fi

# ── 6. Save token ────────────────────────────────────────
echo "$ACCESS_TOKEN" > "$TOKEN_FILE"
echo "Access token saved to $TOKEN_FILE"

# ── 7. Wait for entities to load ─────────────────────────
echo -n "Waiting for MQTT entities to load..."
for i in $(seq 1 30); do
    ENTITY_COUNT=$(curl -sf "${HA_URL}/api/states" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" 2>/dev/null | \
        jq 'length' 2>/dev/null || echo "0")
    if [ "$ENTITY_COUNT" -gt 20 ]; then
        echo " $ENTITY_COUNT entities loaded."
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=== HA Onboarding Complete ==="
echo "URL:      $HA_URL"
echo "User:     demo / demo1234"
echo "Token:    $TOKEN_FILE"
echo "Entities: $ENTITY_COUNT"
