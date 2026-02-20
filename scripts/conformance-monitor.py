#!/usr/bin/env python3
"""Continuous conformance monitor — polls HA and Marge /api/states, compares, logs divergences.

Usage:
    python3 scripts/conformance-monitor.py [--ha-url URL] [--marge-url URL] [--ha-token TOKEN]
        [--interval SECONDS] [--output FILE] [--duration SECONDS] [--quiet]

Requires only Python stdlib (no pip installs).
"""

import argparse
import json
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# --- Configuration -----------------------------------------------------------

EXCLUDE_ENTITY_PATTERNS = [
    re.compile(r"^weather\."),
    re.compile(r"\bmarge\b", re.IGNORECASE),
    re.compile(r"^sensor\.verify_"),
    re.compile(r"^sensor\.scenario_"),
]

VOLATILE_ATTRIBUTES = frozenset({
    "last_changed",
    "last_updated",
    "last_reported",
    "context",
    "assumed_state",
    "icon",
    "supported_features",
})

COMPARED_ATTRIBUTES = [
    "friendly_name",
    "brightness",
    "temperature",
    "color_temp",
]


# --- HTTP helpers ------------------------------------------------------------

def fetch_states(base_url, token=None):
    """GET /api/states from a SUT.  Returns list of entity dicts or None on error."""
    url = base_url.rstrip("/") + "/api/states"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def build_entity_map(states):
    """Convert list of state dicts to {entity_id: dict}."""
    return {s["entity_id"]: s for s in states}


# --- Filtering ---------------------------------------------------------------

def is_excluded(entity_id):
    """Return True if the entity should be skipped during comparison."""
    for pat in EXCLUDE_ENTITY_PATTERNS:
        if pat.search(entity_id):
            return True
    return False


# --- Comparison --------------------------------------------------------------

def compare_entities(ha_map, marge_map):
    """Compare shared entities.  Returns (shared_ids, divergences).

    Each divergence is a dict:
        {"entity_id": str, "field": str, "ha_value": str, "marge_value": str}
    """
    shared = sorted(set(ha_map) & set(marge_map))
    shared = [eid for eid in shared if not is_excluded(eid)]
    divergences = []

    for eid in shared:
        ha = ha_map[eid]
        mg = marge_map[eid]

        # State value (exact string match)
        ha_state = str(ha.get("state", ""))
        mg_state = str(mg.get("state", ""))
        if ha_state != mg_state:
            divergences.append({
                "entity_id": eid,
                "field": "state",
                "ha_value": ha_state,
                "marge_value": mg_state,
            })

        # Key attributes
        ha_attrs = ha.get("attributes", {})
        mg_attrs = mg.get("attributes", {})
        for attr in COMPARED_ATTRIBUTES:
            ha_val = ha_attrs.get(attr)
            mg_val = mg_attrs.get(attr)
            if ha_val is None and mg_val is None:
                continue
            if str(ha_val) != str(mg_val):
                divergences.append({
                    "entity_id": eid,
                    "field": f"attr: {attr}",
                    "ha_value": str(ha_val),
                    "marge_value": str(mg_val),
                })

    return shared, divergences


# --- Output ------------------------------------------------------------------

def ts_short():
    """Return a short HH:MM:SS timestamp for stdout."""
    return datetime.now().strftime("%H:%M:%S")


def ts_iso():
    """Return an ISO 8601 UTC timestamp for JSONL."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def print_poll(poll_num, ha_count, marge_count, shared_count, divergences, quiet):
    """Print one poll cycle to stdout."""
    header = f"[{ts_short()}] Poll #{poll_num} -- HA: {ha_count} entities, Marge: {marge_count} entities, Shared: {shared_count}"
    if quiet and not divergences:
        return
    print(header)
    if not divergences:
        print(f"[{ts_short()}]   All {shared_count} shared entities match")
    else:
        for d in divergences:
            field = d["field"]
            if field == "state":
                print(f"[{ts_short()}]   DIVERGENCE: {d['entity_id']} -- HA: \"{d['ha_value']}\" vs Marge: \"{d['marge_value']}\"")
            else:
                print(f"[{ts_short()}]   DIVERGENCE: {d['entity_id']} -- HA: \"{d['ha_value']}\" vs Marge: \"{d['marge_value']}\" ({field})")


def write_jsonl(fh, poll_num, ha_count, marge_count, shared_count, divergences):
    """Append one JSONL record."""
    record = {
        "timestamp": ts_iso(),
        "poll": poll_num,
        "ha_count": ha_count,
        "marge_count": marge_count,
        "shared": shared_count,
        "divergences": divergences,
    }
    fh.write(json.dumps(record, separators=(",", ":")) + "\n")
    fh.flush()


# --- Summary -----------------------------------------------------------------

def print_summary(start_time, poll_count, all_divergences):
    """Print final summary to stdout."""
    elapsed = time.time() - start_time
    minutes = int(elapsed) // 60
    seconds = int(elapsed) % 60

    entity_counts = {}
    for d in all_divergences:
        key = (d["entity_id"], d["field"])
        entity_counts[key] = entity_counts.get(key, 0) + 1

    # Aggregate by entity_id
    entity_summary = {}
    for (eid, field), count in sorted(entity_counts.items()):
        if eid not in entity_summary:
            entity_summary[eid] = []
        entity_summary[eid].append((field, count))

    print()
    print("=== Conformance Monitor Summary ===")
    print(f"Duration: {minutes}m {seconds}s")
    print(f"Polls: {poll_count}")
    print(f"Total divergences detected: {len(all_divergences)}")
    print(f"Unique divergent entities: {len(entity_summary)}")
    for eid in sorted(entity_summary):
        parts = entity_summary[eid]
        total = sum(c for _, c in parts)
        fields_str = ", ".join(f"{f}" for f, _ in parts)
        label = "divergence" if total == 1 else "divergences"
        print(f"  {eid}: {total} {label} ({fields_str})")


# --- Token loading -----------------------------------------------------------

def load_token(token_arg):
    """Resolve the HA auth token: CLI arg > file > None."""
    if token_arg:
        return token_arg
    token_path = os.path.join(".", "ha-config", ".ha_token")
    if os.path.isfile(token_path):
        with open(token_path, "r") as f:
            t = f.read().strip()
            if t:
                return t
    return None


# --- Main loop ---------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Continuous HA/Marge conformance monitor")
    parser.add_argument("--ha-url", default="http://localhost:8123", help="Home Assistant base URL")
    parser.add_argument("--marge-url", default="http://localhost:8124", help="Marge base URL")
    parser.add_argument("--ha-token", default=None, help="HA long-lived access token")
    parser.add_argument("--interval", type=float, default=5, help="Poll interval in seconds")
    parser.add_argument("--output", default="conformance-log.jsonl", help="JSONL output file path")
    parser.add_argument("--duration", type=float, default=0, help="Run duration in seconds (0 = until Ctrl+C)")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-poll output; only show divergences")
    args = parser.parse_args()

    token = load_token(args.ha_token)

    # Quick connectivity check: warn if HA requires auth and no token
    ha_probe = fetch_states(args.ha_url, token)
    if isinstance(ha_probe, tuple):
        err = ha_probe[1]
        if "401" in err or "403" in err:
            if not token:
                print(f"ERROR: HA returned auth error and no token provided. "
                      f"Use --ha-token or place token in ./ha-config/.ha_token", file=sys.stderr)
                sys.exit(1)

    poll_count = 0
    all_divergences = []
    start_time = time.time()
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    log_fh = open(args.output, "a")

    try:
        while running:
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                break

            poll_count += 1

            # Fetch HA states
            ha_result = fetch_states(args.ha_url, token)
            if isinstance(ha_result, tuple):
                if not args.quiet:
                    print(f"[{ts_short()}] Poll #{poll_count} -- HA fetch error: {ha_result[1]}")
                time.sleep(args.interval)
                continue
            ha_states = ha_result

            # Fetch Marge states
            marge_result = fetch_states(args.marge_url)
            if isinstance(marge_result, tuple):
                if not args.quiet:
                    print(f"[{ts_short()}] Poll #{poll_count} -- Marge fetch error: {marge_result[1]}")
                time.sleep(args.interval)
                continue
            marge_states = marge_result

            ha_map = build_entity_map(ha_states)
            marge_map = build_entity_map(marge_states)

            shared, divergences = compare_entities(ha_map, marge_map)

            print_poll(poll_count, len(ha_states), len(marge_states), len(shared), divergences, args.quiet)
            write_jsonl(log_fh, poll_count, len(ha_states), len(marge_states), len(shared), divergences)

            all_divergences.extend(divergences)

            time.sleep(args.interval)

    finally:
        log_fh.close()
        print_summary(start_time, poll_count, all_divergences)


if __name__ == "__main__":
    main()
