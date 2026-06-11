#!/usr/bin/env python3
"""Particle-type-wise particle-flow performance on (mu=200) ttbar reco outputs.

For each event, match reconstructed PFOs (GaudiPandoraPFOs) to the visible, in-acceptance, stable
truth MC particles (MCParticles) by nearest direction (dR) with an energy-compatibility preference,
then aggregate per particle-type:
  - efficiency  : fraction of truth particles of type T that have a matched PFO
  - response    : median and IQR/median of E_PFO / E_truth for matched pairs
  - mis-ID      : confusion truth-type -> reco-PFO-type (off-diagonal = mis-identification)
  - merging     : fraction of matched PFOs that absorb >1 truth particle (multiplicity per PFO)
  - fake/extra  : PFOs with no truth match (within dR) per event

Runs under the key4hep/podio environment (shifter). Usage:
  pfo_truth_metrics.py --reco f1.root [f2 ...] --out results.json [--max-events N]
      [--eta-acc 3.5] [--min-truth-e 0.5] [--match-dr 0.10]
"""
import argparse
import json
import math
import sys

import numpy as np
from podio import root_io

NU = {12, 14, 16}
PFO_NAMES = ["GaudiPandoraPFOs", "PandoraPFOs"]


def _first(frame, names):
    for n in names:
        try:
            c = frame.get(n)
            if c is not None:
                return c
        except Exception:
            pass
    return None


def _pid(p):
    for acc in ("getPDG", "getType"):
        if hasattr(p, acc):
            return int(getattr(p, acc)())
    return 0


def type_label(pdg, charge):
    a = abs(pdg)
    if a == 22:
        return "photon"
    if a == 11:
        return "electron"
    if a == 13:
        return "muon"
    if abs(charge) > 0.5:
        return "charged_had"
    return "neutral_had"


def eta_phi_e(px, py, pz, e):
    pt = math.hypot(px, py)
    p = math.sqrt(px * px + py * py + pz * pz)
    if p < 1e-9:
        return 0.0, 0.0, e
    eta = math.atanh(max(-0.999999, min(0.999999, pz / p)))
    phi = math.atan2(py, px)
    return eta, phi, e


def dphi(a, b):
    d = a - b
    while d > math.pi:
        d -= 2 * math.pi
    while d < -math.pi:
        d += 2 * math.pi
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reco", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--eta-acc", type=float, default=3.5)
    ap.add_argument("--min-truth-e", type=float, default=0.5)
    ap.add_argument("--match-dr", type=float, default=0.10)
    a = ap.parse_args()

    TYPES = ["photon", "electron", "muon", "charged_had", "neutral_had"]
    # per-type accumulators
    n_truth = {t: 0 for t in TYPES}
    n_truth_matched = {t: 0 for t in TYPES}
    resp = {t: [] for t in TYPES}                 # E_pfo/E_truth for same-type matches
    confusion = {t: {u: 0 for u in TYPES} for t in TYPES}  # truth t -> reco u
    n_events = 0
    n_pfos_total = 0
    n_pfos_fake = 0       # PFO with no truth within dR
    merged_pfo_truth = []  # truth-count per PFO that matched >=1 truth

    for path in a.reco:
        reader = root_io.Reader(path)
        for frame in reader.get("events"):
            if a.max_events and n_events >= a.max_events:
                break
            n_events += 1

            mcs = frame.get("MCParticles")
            pfos = _first(frame, PFO_NAMES)
            if mcs is None or pfos is None:
                continue

            # truth: stable (generatorStatus==1), visible, in acceptance, E>min
            truth = []  # (eta, phi, e, label, idx)
            for m in mcs:
                if int(m.getGeneratorStatus()) != 1:
                    continue
                pdg = int(m.getPDG())
                if abs(pdg) in NU:
                    continue
                mom = m.getMomentum()
                e = float(m.getEnergy())
                if e < a.min_truth_e:
                    continue
                eta, phi, _ = eta_phi_e(mom.x, mom.y, mom.z, e)
                if abs(eta) > a.eta_acc:
                    continue
                lab = type_label(pdg, m.getCharge())
                truth.append([eta, phi, e, lab])

            # pfos
            pf = []  # (eta, phi, e, label)
            for p in pfos:
                m = p.getMomentum()
                e = float(p.getEnergy())
                eta, phi, _ = eta_phi_e(m.x, m.y, m.z, e)
                pf.append([eta, phi, e, type_label(_pid(p), p.getCharge())])
            n_pfos_total += len(pf)

            for t in truth:
                n_truth[t[3]] += 1

            if not truth or not pf:
                n_pfos_fake += len(pf)
                continue

            t_eta = np.array([t[0] for t in truth]); t_phi = np.array([t[1] for t in truth])
            t_e = np.array([t[2] for t in truth])

            # match each truth particle to its nearest PFO (dR), with energy preference as tie-break;
            # track how many truth each PFO absorbs (merging) and which PFOs got used (fakes = unused).
            pfo_truth_count = [0] * len(pf)
            for ti, t in enumerate(truth):
                best, bestcost = -1, 1e9
                for pi, q in enumerate(pf):
                    dr = math.hypot(t[0] - q[0], dphi(t[1], q[1]))
                    if dr > a.match_dr:
                        continue
                    # cost: dR plus a mild energy-mismatch penalty
                    eratio = q[2] / t[2] if t[2] > 0 else 0.0
                    cost = dr + 0.05 * abs(math.log(max(eratio, 1e-3)))
                    if cost < bestcost:
                        bestcost, best = cost, pi
                if best >= 0:
                    n_truth_matched[t[3]] += 1
                    pfo_truth_count[best] += 1
                    confusion[t[3]][pf[best][3]] += 1
                    if pf[best][3] == t[3] and t[2] > 0:
                        resp[t[3]].append(pf[best][2] / t[2])

            for pi in range(len(pf)):
                if pfo_truth_count[pi] == 0:
                    n_pfos_fake += 1
                else:
                    merged_pfo_truth.append(pfo_truth_count[pi])

    # summarise
    def med_iqr(xs):
        if not xs:
            return None, None
        a_ = np.array(xs)
        med = float(np.median(a_))
        q1, q3 = np.percentile(a_, [25, 75])
        return med, (float(q3 - q1) / med if med else None)

    out = {"n_events": n_events, "n_pfos_total": n_pfos_total,
           "n_pfos_fake": n_pfos_fake,
           "fake_pfo_fraction": (n_pfos_fake / n_pfos_total) if n_pfos_total else None,
           "merge_fraction": (sum(1 for c in merged_pfo_truth if c > 1) / len(merged_pfo_truth)) if merged_pfo_truth else None,
           "mean_truth_per_matched_pfo": (float(np.mean(merged_pfo_truth)) if merged_pfo_truth else None),
           "per_type": {}}
    for t in TYPES:
        med, iqr = med_iqr(resp[t])
        eff = (n_truth_matched[t] / n_truth[t]) if n_truth[t] else None
        # mis-id: fraction of matched truth-t reconstructed as a different type
        tot_matched = sum(confusion[t].values())
        misid = (1.0 - confusion[t][t] / tot_matched) if tot_matched else None
        out["per_type"][t] = {
            "n_truth": n_truth[t], "efficiency": eff,
            "response_median": med, "resolution_iqr_over_med": iqr,
            "misid_fraction": misid, "confusion": confusion[t],
        }

    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2)

    # human-readable
    print(f"events={n_events}  PFOs={n_pfos_total}  fake_frac={out['fake_pfo_fraction']}")
    print(f"merge_frac(>1 truth/PFO)={out['merge_fraction']}  mean_truth/matched_PFO={out['mean_truth_per_matched_pfo']}")
    print(f"{'type':<13}{'n_truth':>9}{'eff':>8}{'resp_med':>10}{'res_iqr/m':>11}{'mis-ID':>9}")
    for t in TYPES:
        d = out["per_type"][t]
        def f(x, p="{:.3f}"):
            return p.format(x) if x is not None else "  --"
        print(f"{t:<13}{d['n_truth']:>9}{f(d['efficiency']):>8}{f(d['response_median']):>10}{f(d['resolution_iqr_over_med']):>11}{f(d['misid_fraction']):>9}")


if __name__ == "__main__":
    main()
