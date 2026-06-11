#!/usr/bin/env python3
"""Compute and regression-check particle-flow metrics from k4DetectorPerformance PFONtuple files.

All PF physics evaluation in CI goes through the PFONtuple (k4performance); this tool reduces
each bucket's ntuple to a small metrics dict and diffs it against a committed reference.

  compute: check_pfontuple.py compute -i gamma_E10_eta0=pfontuple_g10.root [-i ...] -o metrics.json
  compare: check_pfontuple.py compare -m metrics.json -r ci/reference/release-alma9/pfo_metrics_ref.json \
               [--ranges ci/validation_ranges.json --profile pfontuple]

Per-bucket metrics (generator-status-1 MC rows only):
  n_mc        number of MC rows
  eff         fraction with a matched reco PFO (has_reco_pfo)
  resp_mean   mean  pfo_E/mc_E of matched rows
  resp_median median pfo_E/mc_E of matched rows
  resp_iqr    IQR of pfo_E/mc_E (matched)
  n_pfo_mean  mean number of PFOs linked to the MC particle (nPFOs)

Default tolerances (overridable via the 'pfontuple' profile in validation_ranges.json):
  resp_mean/resp_median: |delta| <= 0.03 ; eff: |delta| <= 0.02 (absolute)
  resp_iqr: 10% relative ; n_pfo_mean: 5% relative (with 0.1 absolute floor for low stats)
"""

import argparse
import json
import sys

DEFAULT_TOL = {
    "resp_mean": {"abs": 0.03},
    "resp_median": {"abs": 0.03},
    "eff": {"abs": 0.02},
    "resp_iqr": {"rel": 0.10, "abs_floor": 0.02},
    "n_pfo_mean": {"rel": 0.05, "abs_floor": 0.10},
}


def quantile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def bucket_metrics(path):
    import ROOT

    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        raise SystemExit(f"cannot open {path}")
    t = f.Get("PFONtuple")
    if not t:
        raise SystemExit(f"no PFONtuple tree in {path}")

    n_mc = 0
    matched = 0
    resp = []
    npfos = []
    for e in t:
        if int(e.mc_genStatus) != 1:
            continue
        n_mc += 1
        npfos.append(float(e.nPFOs))
        if bool(e.has_reco_pfo) and e.mc_E > 0:
            matched += 1
            resp.append(float(e.pfo_E) / float(e.mc_E))
    resp.sort()
    return {
        "n_mc": n_mc,
        "eff": matched / n_mc if n_mc else 0.0,
        "resp_mean": sum(resp) / len(resp) if resp else 0.0,
        "resp_median": quantile(resp, 0.5),
        "resp_iqr": quantile(resp, 0.75) - quantile(resp, 0.25),
        "n_pfo_mean": sum(npfos) / len(npfos) if npfos else 0.0,
    }


def cmd_compute(args):
    out = {}
    for spec in args.input:
        if "=" not in spec:
            raise SystemExit(f"--input must be bucket=path, got: {spec}")
        bucket, path = spec.split("=", 1)
        out[bucket] = bucket_metrics(path)
        print(f"[pfontuple] {bucket}: " + ", ".join(f"{k}={v:.4g}" for k, v in out[bucket].items()))
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print(f"[pfontuple] wrote {args.output}")
    return 0


def tol_for(metric, ranges):
    return ranges.get(metric, DEFAULT_TOL.get(metric, {"abs": 0.0}))


def cmd_compare(args):
    with open(args.metrics, encoding="utf-8") as fh:
        metrics = json.load(fh)
    with open(args.reference, encoding="utf-8") as fh:
        reference = json.load(fh)
    ranges = {}
    if args.ranges:
        with open(args.ranges, encoding="utf-8") as fh:
            ranges = json.load(fh).get(args.profile, {})

    failures = []
    for bucket, ref in sorted(reference.items()):
        got = metrics.get(bucket)
        if got is None:
            failures.append(f"{bucket}: MISSING from computed metrics")
            continue
        for metric, ref_val in ref.items():
            if metric == "n_mc":
                if got.get(metric, 0) < 0.5 * ref_val:
                    failures.append(f"{bucket}.{metric}: {got.get(metric)} << reference {ref_val}")
                continue
            tol = tol_for(metric, ranges)
            val = got.get(metric, 0.0)
            delta = abs(val - ref_val)
            if "abs" in tol:
                limit = tol["abs"]
            else:
                limit = max(tol.get("rel", 0.0) * abs(ref_val), tol.get("abs_floor", 0.0))
            status = "OK" if delta <= limit else "FAIL"
            print(f"[pfontuple] {bucket}.{metric}: {val:.4f} vs ref {ref_val:.4f} "
                  f"(|d|={delta:.4f} <= {limit:.4f}) {status}")
            if status == "FAIL":
                failures.append(f"{bucket}.{metric}: {val:.4f} vs {ref_val:.4f} (limit {limit:.4f})")

    extra = sorted(set(metrics) - set(reference))
    if extra:
        print(f"[pfontuple] note: buckets without reference (not checked): {extra}")

    if failures:
        print("[pfontuple] FAILED checks:")
        for f_ in failures:
            print("  - " + f_)
        return 1
    print("[pfontuple] all checks passed")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compute")
    c.add_argument("-i", "--input", action="append", required=True,
                   help="bucket=pfontuple.root (repeatable)")
    c.add_argument("-o", "--output", required=True)
    d = sub.add_parser("compare")
    d.add_argument("-m", "--metrics", required=True)
    d.add_argument("-r", "--reference", required=True)
    d.add_argument("--ranges", default="")
    d.add_argument("--profile", default="pfontuple")
    args = ap.parse_args()
    return cmd_compute(args) if args.cmd == "compute" else cmd_compare(args)


if __name__ == "__main__":
    sys.exit(main())
