#!/usr/bin/env python3
"""
CTS Divergence Matrix — compare pytest-json-report results from HA and Marge.

Reads two pytest-json-report JSON files and produces a four-quadrant
divergence matrix:

  1. both-pass:           Test passes on both HA and Marge
  2. both-fail:           Test fails on both (expected parity — feature missing or test wrong)
  3. ha-pass-marge-fail:  HA passes, Marge fails — REAL DIVERGENCE (bugs in Marge)
  4. marge-pass-ha-fail:  Marge passes, HA fails — Marge-specific or wrong expectations

Exit code 0 if ha-pass-marge-fail count is 0, exit 1 otherwise.

Usage:
    python3 scripts/cts-compare.py ha-report.json marge-report.json [--verbose] [--output matrix.json]
"""

import argparse
import json
import sys
from pathlib import Path


def load_report(path: Path) -> dict[str, str]:
    """Load a pytest-json-report file and return {nodeid: outcome} mapping.

    Skipped tests are excluded from the returned mapping.
    Outcome values: "passed", "failed", "error".
    """
    with open(path, "r") as f:
        data = json.load(f)

    results = {}
    for test in data.get("tests", []):
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")

        # Exclude skipped tests from analysis
        if outcome == "skipped":
            continue

        # Treat "error" the same as "failed" for matrix purposes
        if outcome == "error":
            outcome = "failed"

        results[nodeid] = outcome

    return results


def compute_matrix(
    ha_results: dict[str, str], marge_results: dict[str, str]
) -> dict[str, list[str]]:
    """Compute the four-quadrant divergence matrix.

    Only considers tests present in BOTH reports (intersection).
    Returns dict with four keys, each mapping to a sorted list of nodeids.
    """
    common_tests = sorted(set(ha_results.keys()) & set(marge_results.keys()))

    matrix = {
        "both_pass": [],
        "both_fail": [],
        "ha_pass_marge_fail": [],
        "marge_pass_ha_fail": [],
    }

    for nodeid in common_tests:
        ha_outcome = ha_results[nodeid]
        marge_outcome = marge_results[nodeid]

        ha_pass = ha_outcome == "passed"
        marge_pass = marge_outcome == "passed"

        if ha_pass and marge_pass:
            matrix["both_pass"].append(nodeid)
        elif not ha_pass and not marge_pass:
            matrix["both_fail"].append(nodeid)
        elif ha_pass and not marge_pass:
            matrix["ha_pass_marge_fail"].append(nodeid)
        elif not ha_pass and marge_pass:
            matrix["marge_pass_ha_fail"].append(nodeid)

    return matrix


def compute_only_in(
    ha_results: dict[str, str], marge_results: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Find tests present in only one report (after skipped exclusion).

    Returns (only_in_ha, only_in_marge) as sorted lists of nodeids.
    """
    ha_keys = set(ha_results.keys())
    marge_keys = set(marge_results.keys())
    only_ha = sorted(ha_keys - marge_keys)
    only_marge = sorted(marge_keys - ha_keys)
    return only_ha, only_marge


def print_matrix(
    matrix: dict[str, list[str]],
    only_ha: list[str],
    only_marge: list[str],
    verbose: bool,
) -> None:
    """Print the divergence matrix summary to stdout."""
    total = sum(len(v) for v in matrix.values())

    def pct(n: int) -> str:
        if total == 0:
            return " 0.0%"
        return f"{100 * n / total:5.1f}%"

    bp = len(matrix["both_pass"])
    bf = len(matrix["both_fail"])
    hpmf = len(matrix["ha_pass_marge_fail"])
    mphf = len(matrix["marge_pass_ha_fail"])

    print()
    print("=== CTS Divergence Matrix ===")
    print(f"Total tests analyzed: {total}")
    print()
    print(f"  Both pass:            {bp:>5} ({pct(bp)})")
    print(f"  Both fail:            {bf:>5} ({pct(bf)})")
    print(
        f"  HA pass / Marge fail: {hpmf:>5} ({pct(hpmf)})  <- DIVERGENCE"
    )
    print(f"  Marge pass / HA fail: {mphf:>5} ({pct(mphf)})")

    if only_ha or only_marge:
        print()
        print(f"  Only in HA report:    {len(only_ha):>5}  (not run against Marge)")
        print(f"  Only in Marge report: {len(only_marge):>5}  (not run against HA)")

    # Always show ha-pass/marge-fail list (the real divergences)
    if hpmf > 0:
        print()
        print("HA-pass / Marge-fail (divergences):")
        for nodeid in matrix["ha_pass_marge_fail"]:
            print(f"  {nodeid}")

    if verbose:
        if mphf > 0:
            print()
            print("Marge-pass / HA-fail:")
            for nodeid in matrix["marge_pass_ha_fail"]:
                print(f"  {nodeid}")

        if bf > 0:
            print()
            print("Both fail:")
            for nodeid in matrix["both_fail"]:
                print(f"  {nodeid}")

        if only_ha:
            print()
            print("Only in HA report (skipped or not run against Marge):")
            for nodeid in only_ha:
                print(f"  {nodeid}")

        if only_marge:
            print()
            print("Only in Marge report (skipped or not run against HA):")
            for nodeid in only_marge:
                print(f"  {nodeid}")

    print()


def write_json_output(
    path: Path,
    matrix: dict[str, list[str]],
    only_ha: list[str],
    only_marge: list[str],
) -> None:
    """Write machine-readable JSON summary to file."""
    total = sum(len(v) for v in matrix.values())
    output = {
        "total_analyzed": total,
        "counts": {
            "both_pass": len(matrix["both_pass"]),
            "both_fail": len(matrix["both_fail"]),
            "ha_pass_marge_fail": len(matrix["ha_pass_marge_fail"]),
            "marge_pass_ha_fail": len(matrix["marge_pass_ha_fail"]),
            "only_in_ha": len(only_ha),
            "only_in_marge": len(only_marge),
        },
        "tests": {
            "both_pass": matrix["both_pass"],
            "both_fail": matrix["both_fail"],
            "ha_pass_marge_fail": matrix["ha_pass_marge_fail"],
            "marge_pass_ha_fail": matrix["marge_pass_ha_fail"],
            "only_in_ha": only_ha,
            "only_in_marge": only_marge,
        },
    }
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")
    print(f"JSON summary written to: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CTS Divergence Matrix — compare HA and Marge pytest-json-report results"
    )
    parser.add_argument(
        "ha_report",
        type=Path,
        help="Path to HA pytest-json-report JSON file",
    )
    parser.add_argument(
        "marge_report",
        type=Path,
        help="Path to Marge pytest-json-report JSON file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show full test names in all quadrants",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON summary to this file",
    )
    args = parser.parse_args()

    # Validate input files exist
    if not args.ha_report.is_file():
        print(f"Error: HA report not found: {args.ha_report}", file=sys.stderr)
        return 2
    if not args.marge_report.is_file():
        print(f"Error: Marge report not found: {args.marge_report}", file=sys.stderr)
        return 2

    # Load and parse reports
    ha_results = load_report(args.ha_report)
    marge_results = load_report(args.marge_report)

    print(f"HA report:    {len(ha_results)} tests (excluding skipped)")
    print(f"Marge report: {len(marge_results)} tests (excluding skipped)")

    # Compute matrix (intersection only)
    matrix = compute_matrix(ha_results, marge_results)
    only_ha, only_marge = compute_only_in(ha_results, marge_results)

    # Print human-readable summary
    print_matrix(matrix, only_ha, only_marge, args.verbose)

    # Write JSON if requested
    if args.output:
        write_json_output(args.output, matrix, only_ha, only_marge)

    # Exit code: 0 if no real divergences, 1 otherwise
    divergence_count = len(matrix["ha_pass_marge_fail"])
    if divergence_count > 0:
        print(f"FAIL: {divergence_count} divergence(s) found (HA pass / Marge fail)")
        return 1
    else:
        print("PASS: No divergences (all HA-passing tests also pass on Marge)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
