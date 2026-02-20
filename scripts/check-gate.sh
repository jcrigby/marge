#!/bin/bash
# check-gate.sh — Verify gate milestones
#
# Usage: ./scripts/check-gate.sh <gate-name>
# Gates: ha, marge, cts-ha, cts-marge, conformance

set -euo pipefail

GATE="${1:-}"

case "$GATE" in
  ha)
    echo "=== GATE-HA: Checking HA baseline ==="
    HA_URL="${HA_URL:-http://localhost:8123}"
    TOKEN=$(cat ./ha-config/.ha_token 2>/dev/null || echo "")
    AUTH=""
    if [ -n "$TOKEN" ]; then
      AUTH="-H \"Authorization: Bearer $TOKEN\""
    fi

    # Check API responds
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer $TOKEN" \
      "$HA_URL/api/" 2>/dev/null || echo "000")
    if [ "$STATUS" != "200" ]; then
      echo "FAIL: HA API returned $STATUS"
      exit 1
    fi
    echo "  API: OK ($STATUS)"

    # Check entity count
    COUNT=$(curl -sf -H "Authorization: Bearer $TOKEN" \
      "$HA_URL/api/states" 2>/dev/null | jq 'length')
    echo "  Entities: $COUNT"
    if [ "$COUNT" -lt 20 ]; then
      echo "FAIL: Expected >= 20 entities, got $COUNT"
      exit 1
    fi
    echo "=== GATE-HA: PASSED ==="
    ;;

  marge)
    echo "=== GATE-MARGE: Checking Marge ==="
    MARGE_URL="${MARGE_URL:-http://localhost:8124}"

    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" \
      "$MARGE_URL/api/" 2>/dev/null || echo "000")
    if [ "$STATUS" != "200" ]; then
      echo "FAIL: Marge API returned $STATUS"
      exit 1
    fi
    echo "  API: OK ($STATUS)"

    HEALTH=$(curl -sf "$MARGE_URL/api/health" 2>/dev/null)
    echo "  Health: $HEALTH"
    echo "=== GATE-MARGE: PASSED ==="
    ;;

  cts-ha)
    echo "=== GATE-CTS-HA: Running CTS against HA ==="
    SUT_URL="${HA_URL:-http://localhost:8123}" \
    SUT_TOKEN=$(cat ./ha-config/.ha_token 2>/dev/null || echo "") \
    SUT_MQTT_HOST="${HA_MQTT_HOST:-localhost}" \
    SUT_MQTT_PORT="${HA_MQTT_PORT:-1883}" \
    pytest tests/ -v --json-report --json-report-file=cts-ha-results.json
    echo "=== GATE-CTS-HA: See results above ==="
    ;;

  cts-marge)
    echo "=== GATE-CTS-MARGE: Running CTS against Marge ==="
    SUT_URL="${MARGE_URL:-http://localhost:8124}" \
    SUT_MQTT_HOST="${MARGE_MQTT_HOST:-localhost}" \
    SUT_MQTT_PORT="${MARGE_MQTT_PORT:-1884}" \
    pytest tests/ -v --json-report --json-report-file=cts-marge-results.json
    echo "=== GATE-CTS-MARGE: See results above ==="
    ;;

  conformance)
    echo "=== GATE-CONFORMANCE: Dual CTS + Divergence Matrix ==="
    RESULTS_DIR="cts-results/gate-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$RESULTS_DIR"

    # Run CTS against HA (allow failures — we capture exit code)
    echo "--- Running CTS against HA ---"
    SUT_URL="${HA_URL:-http://localhost:8123}" \
    SUT_TOKEN=$(cat ./ha-config/.ha_token 2>/dev/null || echo "") \
    SUT_MQTT_HOST="${HA_MQTT_HOST:-localhost}" \
    SUT_MQTT_PORT="${HA_MQTT_PORT:-1883}" \
    pytest tests/ -v --json-report --json-report-file="$RESULTS_DIR/ha-report.json" --timeout=30 2>&1 | tee "$RESULTS_DIR/ha-output.log" || true

    echo ""
    echo "--- Running CTS against Marge ---"
    SUT_URL="${MARGE_URL:-http://localhost:8124}" \
    SUT_MQTT_HOST="${MARGE_MQTT_HOST:-localhost}" \
    SUT_MQTT_PORT="${MARGE_MQTT_PORT:-1884}" \
    pytest tests/ -v --json-report --json-report-file="$RESULTS_DIR/marge-report.json" --timeout=30 2>&1 | tee "$RESULTS_DIR/marge-output.log" || true

    echo ""
    echo "--- Comparing results ---"
    if [ ! -f "$RESULTS_DIR/ha-report.json" ] || [ ! -f "$RESULTS_DIR/marge-report.json" ]; then
      echo "FAIL: One or both report files missing"
      exit 1
    fi

    python3 scripts/cts-compare.py "$RESULTS_DIR/ha-report.json" "$RESULTS_DIR/marge-report.json" \
      --verbose --output "$RESULTS_DIR/matrix.json"
    COMPARE_RC=$?

    echo ""
    echo "Results saved to: $RESULTS_DIR/"
    if [ $COMPARE_RC -eq 0 ]; then
      echo "=== GATE-CONFORMANCE: PASSED (zero HA-pass/Marge-fail divergences) ==="
    else
      echo "=== GATE-CONFORMANCE: FAILED (divergences found) ==="
    fi
    exit $COMPARE_RC
    ;;

  *)
    echo "Usage: $0 <gate-name>"
    echo "Gates: ha, marge, cts-ha, cts-marge, conformance"
    exit 1
    ;;
esac
