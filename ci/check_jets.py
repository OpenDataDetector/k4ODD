#!/usr/bin/env python3
"""Regression-check a jet_analysis.py summary JSON against a committed reference.

  check_jets.py -m ttbar_summary.json -r ci/reference/release-alma9/jet_metrics_ref.json

The reference file maps dotted keys into the summary to [expected, tolerance, mode]:
  { "jet_E_response.median": [0.977, 0.03, "abs"],
    "jet_E_response.iqr_over_med": [0.16, 0.10, "rel"],
    "n_matched_jets": [120, 0.25, "rel"] }
"""

import argparse
import json
import sys


def dig(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--metrics", required=True, help="jet_analysis *_summary.json")
    ap.add_argument("-r", "--reference", required=True)
    args = ap.parse_args()
    with open(args.metrics, encoding="utf-8") as fh:
        metrics = json.load(fh)
    with open(args.reference, encoding="utf-8") as fh:
        reference = json.load(fh)

    failures = []
    for key, spec in sorted(reference.items()):
        expected, tol, mode = spec[0], spec[1], (spec[2] if len(spec) > 2 else "abs")
        val = dig(metrics, key)
        if val is None:
            failures.append(f"{key}: missing from summary")
            continue
        limit = tol if mode == "abs" else tol * abs(expected)
        delta = abs(float(val) - float(expected))
        status = "OK" if delta <= limit else "FAIL"
        print(f"[jets] {key}: {val:.4g} vs ref {expected:.4g} (|d|={delta:.4g} <= {limit:.4g}) {status}")
        if status == "FAIL":
            failures.append(f"{key}: {val:.4g} vs {expected:.4g} (limit {limit:.4g})")

    if failures:
        print("[jets] FAILED checks:")
        for f_ in failures:
            print("  - " + f_)
        return 1
    print("[jets] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
