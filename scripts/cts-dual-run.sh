#!/bin/bash
#
# cts-dual-run.sh — Run CTS against both HA and Marge, then compare results.
#
# Orchestrates two pytest runs (one against HA, one against Marge), stores
# results in a timestamped directory, and calls cts-compare.py to produce
# a four-quadrant divergence matrix.
#
# Environment variable overrides:
#   HA_URL           HA base URL           (default: http://localhost:8123)
#   MARGE_URL        Marge base URL        (default: http://localhost:8124)
#   HA_MQTT_HOST     HA MQTT broker host   (default: localhost)
#   HA_MQTT_PORT     HA MQTT broker port   (default: 1883)
#   MARGE_MQTT_HOST  Marge MQTT broker host (default: localhost)
#   MARGE_MQTT_PORT  Marge MQTT broker port (default: 1884)
#
# Usage:
#   ./scripts/cts-dual-run.sh
#
# Output:
#   cts-results/<timestamp>/
#     ha-report.json      pytest-json-report from HA run
#     marge-report.json   pytest-json-report from Marge run
#     ha-output.log       Full pytest stdout/stderr from HA run
#     marge-output.log    Full pytest stdout/stderr from Marge run
#     matrix.json         Machine-readable divergence matrix
#
# Exit code: 0 if no HA-pass/Marge-fail divergences, 1 otherwise.

# --- Configuration (with environment variable overrides) ---

HA_URL="${HA_URL:-http://localhost:8123}"
MARGE_URL="${MARGE_URL:-http://localhost:8124}"
HA_MQTT_HOST="${HA_MQTT_HOST:-localhost}"
HA_MQTT_PORT="${HA_MQTT_PORT:-1883}"
MARGE_MQTT_HOST="${MARGE_MQTT_HOST:-localhost}"
MARGE_MQTT_PORT="${MARGE_MQTT_PORT:-1884}"

# --- Resolve project root (script lives in scripts/) ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Create timestamped results directory ---

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RESULTS_DIR="${PROJECT_ROOT}/cts-results/${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

echo "============================================"
echo "  CTS Dual Run — $(date)"
echo "============================================"
echo ""
echo "  HA URL:         $HA_URL"
echo "  Marge URL:      $MARGE_URL"
echo "  HA MQTT:        $HA_MQTT_HOST:$HA_MQTT_PORT"
echo "  Marge MQTT:     $MARGE_MQTT_HOST:$MARGE_MQTT_PORT"
echo "  Results dir:    $RESULTS_DIR"
echo ""

# --- Read HA token if available ---

HA_TOKEN=""
HA_TOKEN_FILE="${PROJECT_ROOT}/ha-config/.ha_token"
if [ -f "$HA_TOKEN_FILE" ]; then
    HA_TOKEN="$(cat "$HA_TOKEN_FILE")"
    echo "  HA token:       loaded from $HA_TOKEN_FILE"
else
    echo "  HA token:       not found (some tests may fail)"
fi
echo ""

# --- Run CTS against HA ---

echo "============================================"
echo "  Running CTS against HA ($HA_URL)"
echo "============================================"
echo ""

SUT_URL="$HA_URL" \
SUT_TOKEN="$HA_TOKEN" \
SUT_MQTT_HOST="$HA_MQTT_HOST" \
SUT_MQTT_PORT="$HA_MQTT_PORT" \
pytest "${PROJECT_ROOT}/tests/" \
    -v \
    --json-report \
    --json-report-file="$RESULTS_DIR/ha-report.json" \
    --timeout=30 \
    2>&1 | tee "$RESULTS_DIR/ha-output.log"

HA_EXIT=$?
echo ""
echo "  HA pytest exit code: $HA_EXIT"
echo ""

# --- Run CTS against Marge ---

echo "============================================"
echo "  Running CTS against Marge ($MARGE_URL)"
echo "============================================"
echo ""

SUT_URL="$MARGE_URL" \
SUT_MQTT_HOST="$MARGE_MQTT_HOST" \
SUT_MQTT_PORT="$MARGE_MQTT_PORT" \
pytest "${PROJECT_ROOT}/tests/" \
    -v \
    --json-report \
    --json-report-file="$RESULTS_DIR/marge-report.json" \
    --timeout=30 \
    2>&1 | tee "$RESULTS_DIR/marge-output.log"

MARGE_EXIT=$?
echo ""
echo "  Marge pytest exit code: $MARGE_EXIT"
echo ""

# --- Compare results ---

echo "============================================"
echo "  Comparing results"
echo "============================================"
echo ""

# Verify both report files were generated
if [ ! -f "$RESULTS_DIR/ha-report.json" ]; then
    echo "ERROR: HA report not generated at $RESULTS_DIR/ha-report.json"
    echo "  Check $RESULTS_DIR/ha-output.log for details"
    exit 2
fi

if [ ! -f "$RESULTS_DIR/marge-report.json" ]; then
    echo "ERROR: Marge report not generated at $RESULTS_DIR/marge-report.json"
    echo "  Check $RESULTS_DIR/marge-output.log for details"
    exit 2
fi

python3 "$SCRIPT_DIR/cts-compare.py" \
    "$RESULTS_DIR/ha-report.json" \
    "$RESULTS_DIR/marge-report.json" \
    --verbose \
    --output "$RESULTS_DIR/matrix.json"

COMPARE_EXIT=$?

echo ""
echo "============================================"
echo "  Results saved to: $RESULTS_DIR"
echo "============================================"
echo ""
echo "  ha-report.json    — HA pytest results"
echo "  marge-report.json — Marge pytest results"
echo "  ha-output.log     — HA pytest output"
echo "  marge-output.log  — Marge pytest output"
echo "  matrix.json       — Divergence matrix (JSON)"
echo ""

exit $COMPARE_EXIT
