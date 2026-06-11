#!/usr/bin/env python3
"""Stage 2 — calorimeter energy-SCALE calibration (ideal or realistic digi).

Orchestrates reco-only runs on the cached sim grid (via srun reco_iter.sh + _metrics.sh)
and solves for the EM and hadronic GeV-scale factors that put single-particle response at 1.0.

- EM scale: single γ. Lever = ECalToEMGeVCalibration (+ HCalToEMGeVCalibration). Small (~×1.02).
- HAD scale: single n & K_L at a high reference energy (SC-insensitive). Lever = the three
  Pandora HAD constants scaled by a common factor (ECalToHadGeVCalibration{Barrel,EndCap},
  HCalToHadGeVCalibration) — the ECAL-had term dominates for ODD (deep ECAL).
Both via a 2-point linear solve (response is ~linear in the scale factor over a modest range).

Writes export lines to --out (sourced by later stages). Run on a node with the cached sims ready:
    python3 calibrate_scale.py --salloc <jobid> --grid-dir testbed/runs/calib_grid \
        --out testbed/results/calib_constants.env [--had-eref 50.0] [--extra-env KEY=VAL ...]
"""
import argparse, json, subprocess, sys, os

REPO = os.environ.get("K4ODD_WORKDIR", ".")
# base (pre-calibration) Pandora scale constants from ODDreconstruction.py
BASE = {
    "ECAL_EM": 1.01776966108,
    "HCAL_EM": 1.01776966108,
    "ECAL_HAD_BARREL": 1.11490774181,
    "ECAL_HAD_ENDCAP": 1.11490774181,
    "HCAL_HAD": 1.00565042407,
}


def sh(cmd, timeout=400):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def reco(salloc, sim, out, overrides, extra_env):
    env = " ".join(f"{k}={v}" for k, v in {**extra_env, **overrides}.items())
    cmd = (f"srun --jobid={salloc} --overlap -n1 -c4 env {env} "
           f"bash {REPO}/testbed/scripts/reco_iter.sh {sim} {out}")
    r = sh(cmd, timeout=500)
    return os.path.exists(out)


def metric(salloc, reco_path, etrue, pdg, charged):
    cmd = (f"srun --jobid={salloc} --overlap -n1 -c4 "
           f"bash {REPO}/testbed/scripts/_metrics.sh {reco_path} {etrue} {pdg} {charged}")
    r = sh(cmd, timeout=200)
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return None


def linear_solve(p0, p1):
    """(f0,r0),(f1,r1) -> factor f* giving r=1."""
    (f0, r0), (f1, r1) = p0, p1
    b = (r1 - r0) / (f1 - f0)
    a = r0 - b * f0
    if abs(b) < 1e-6:
        return 1.0
    fstar = (1.0 - a) / b
    return max(0.3, min(5.0, fstar))


def measure_response(salloc, grid_dir, particle, energy, pdg, charged, overrides, extra_env, tag):
    sim = f"{grid_dir}/{particle}_E{energy}_eta0.5/sim_with_tracks.root"
    if not os.path.exists(sim):
        print(f"  [skip] missing sim {sim}", flush=True)
        return None
    out = f"{grid_dir}/{particle}_E{energy}_eta0.5/reco_{tag}.root"
    if not reco(salloc, sim, out, overrides, extra_env):
        print(f"  [fail] reco {particle} E{energy} {tag}", flush=True)
        return None
    m = metric(salloc, out, energy, pdg, charged)
    return m["median_response"] if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salloc", required=True)
    ap.add_argument("--grid-dir", default=f"{REPO}/testbed/runs/calib_grid")
    ap.add_argument("--out", default=f"{REPO}/testbed/results/calib_constants.env")
    ap.add_argument("--had-eref", default="50.0")
    ap.add_argument("--em-eref", default="10.0")
    ap.add_argument("--extra-env", nargs="*", default=[], help="KEY=VAL passed to every reco (e.g. realistic-digi flags)")
    args = ap.parse_args()
    extra_env = dict(kv.split("=", 1) for kv in args.extra_env)

    print(f"=== Stage 2 scale calibration (extra_env={extra_env}) ===", flush=True)

    # ---- EM scale (gamma) ----
    print("[EM] gamma @", args.em_eref, "GeV", flush=True)
    em_pts = []
    for f in (1.0, 1.05):
        ov = {"K4ODD_ECAL_EM_SCALE": BASE["ECAL_EM"] * f, "K4ODD_HCAL_EM_SCALE": BASE["HCAL_EM"] * f}
        r = measure_response(args.salloc, args.grid_dir, "gamma", args.em_eref, 22, 0, ov, extra_env, f"em{f}")
        print(f"  EM factor {f}: resp={r}", flush=True)
        if r is not None:
            em_pts.append((f, r))
    em_factor = linear_solve(em_pts[0], em_pts[1]) if len(em_pts) == 2 else 1.0
    print(f"[EM] solved factor = {em_factor:.4f}", flush=True)

    # ---- HAD scale (neutron + kaon0L at high E ref) ----
    print("[HAD] neutron+kaon0L @", args.had_eref, "GeV", flush=True)
    had_pts = []
    for f in (1.0, 1.4):
        ov = {
            "K4ODD_ECAL_HAD_SCALE_BARREL": BASE["ECAL_HAD_BARREL"] * f,
            "K4ODD_ECAL_HAD_SCALE_ENDCAP": BASE["ECAL_HAD_ENDCAP"] * f,
            "K4ODD_HCAL_HAD_SCALE": BASE["HCAL_HAD"] * f,
        }
        rs = []
        for part, pdg in (("neutron", 2112), ("kaon0L", 130)):
            r = measure_response(args.salloc, args.grid_dir, part, args.had_eref, pdg, 0, ov, extra_env, f"had{f}")
            if r is not None:
                rs.append(r)
            print(f"  HAD factor {f} {part}: resp={r}", flush=True)
        if rs:
            had_pts.append((f, sum(rs) / len(rs)))
    had_factor = linear_solve(had_pts[0], had_pts[1]) if len(had_pts) == 2 else 1.0
    print(f"[HAD] solved factor = {had_factor:.4f}", flush=True)

    # ---- write calibrated constants ----
    consts = {
        "K4ODD_ECAL_EM_SCALE": BASE["ECAL_EM"] * em_factor,
        "K4ODD_HCAL_EM_SCALE": BASE["HCAL_EM"] * em_factor,
        "K4ODD_ECAL_HAD_SCALE_BARREL": BASE["ECAL_HAD_BARREL"] * had_factor,
        "K4ODD_ECAL_HAD_SCALE_ENDCAP": BASE["ECAL_HAD_ENDCAP"] * had_factor,
        "K4ODD_HCAL_HAD_SCALE": BASE["HCAL_HAD"] * had_factor,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(f"# Stage 2 calibrated calo scale (em_factor={em_factor:.4f}, had_factor={had_factor:.4f})\n")
        for k, v in {**extra_env, **consts}.items():
            fh.write(f"export {k}={v}\n")
    print(f"=== wrote {args.out} ===", flush=True)
    for k, v in consts.items():
        print(f"  {k}={v}", flush=True)


if __name__ == "__main__":
    main()
