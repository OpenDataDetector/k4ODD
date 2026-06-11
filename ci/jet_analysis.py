#!/usr/bin/env python3
"""Jet-level particle-flow validation on ODD Pandora reco files.

For each event: cluster PFOs and (visible, in-acceptance) truth particles with anti-kt R=0.4,
match reco jets to truth jets in dR, and measure the jet energy/pT response. Aggregates over
all events/files and writes a summary JSON (+ optional raw-array npz + a response figure).

Pileup-aware options (for mu=200, where every R=0.4 cone collects pileup):
  --pileup-subtract : grid-median rho (GridMedianBackgroundEstimator-style) area subtraction on
                      the RECO jets (pt -> pt - rho*pi*R^2), so matched reco pt tracks the hard jet.
  --leading-n N     : evaluate only the N highest-pT TRUTH jets/event (the hard-scatter jets,
                      which dominate the high-pT tail above the pileup), instead of all jets.

Usage: jet_analysis.py --reco f1.root [f2 ...] --out-prefix results/jets [--R 0.4] [--min-jet-pt 10]
                       [--eta-acc 3.5] [--label "..."] [--pileup-subtract] [--leading-n 6] [--dump]
"""
import argparse, glob, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot
import fastjet
import awkward as ak

NU = {12, 14, 16}

PFO_BRANCHES = [
    "GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.x", "GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.y",
    "GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.z", "GaudiPandoraPFOs/GaudiPandoraPFOs.energy",
    "MCParticles/MCParticles.PDG", "MCParticles/MCParticles.generatorStatus",
    "MCParticles/MCParticles.momentum.x", "MCParticles/MCParticles.momentum.y",
    "MCParticles/MCParticles.momentum.z", "MCParticles/MCParticles.mass",
]


def cluster_jets(px, py, pz, E, R, min_pt):
    """Anti-kt cluster one event's particles -> array of (E,pt,eta,phi) jets, pt-sorted desc."""
    if len(E) == 0:
        return np.empty((0, 4))
    parts = ak.Array([[{"px": float(a), "py": float(b), "pz": float(c), "E": float(d)}
                       for a, b, c, d in zip(px, py, pz, E)]])
    jetdef = fastjet.JetDefinition(fastjet.antikt_algorithm, R)
    cs = fastjet.ClusterSequence(parts, jetdef)
    jets = cs.inclusive_jets(min_pt=min_pt)[0]
    out = []
    for j in jets:
        jpx, jpy, jpz, jE = float(j.px), float(j.py), float(j.pz), float(j.E)
        pt = np.hypot(jpx, jpy)
        p = np.sqrt(jpx**2 + jpy**2 + jpz**2)
        eta = np.arctanh(np.clip(jpz / max(p, 1e-9), -0.999999, 0.999999))
        phi = np.arctan2(jpy, jpx)
        out.append((jE, pt, eta, phi))
    if not out:
        return np.empty((0, 4))
    arr = np.array(out)
    return arr[np.argsort(-arr[:, 1])]  # sort by pt desc


def dphi(a, b):
    d = a - b
    return (d + np.pi) % (2 * np.pi) - np.pi


def grid_rho(eta, phi, pt, eta_acc, cell=0.55):
    """Grid-median pileup density rho [GeV/area]: median over eta-phi cells of (sum pt)/(cell area).
    Standard GridMedianBackgroundEstimator; cells with 0 pt are kept (median over the full grid)."""
    if len(pt) == 0:
        return 0.0
    neta = max(1, int(round(2 * eta_acc / cell)))
    nphi = max(1, int(round(2 * np.pi / cell)))
    aedge = np.linspace(-eta_acc, eta_acc, neta + 1)
    pedge = np.linspace(-np.pi, np.pi, nphi + 1)
    insel = np.abs(eta) < eta_acc
    if not np.any(insel):
        return 0.0
    H, _, _ = np.histogram2d(eta[insel], phi[insel], bins=[aedge, pedge], weights=pt[insel])
    cell_area = (aedge[1] - aedge[0]) * (pedge[1] - pedge[0])
    return float(np.median(H) / cell_area)


def subtract_pileup(jets, rho, R):
    """Scalar area subtraction: pt -> pt - rho*pi*R^2; drop jets with pt<=0; scale 4-vec (E) by pt ratio."""
    if len(jets) == 0 or rho <= 0:
        return jets
    area = np.pi * R * R
    out = jets.copy()
    pt_corr = out[:, 1] - rho * area
    keep = pt_corr > 0
    out = out[keep]
    ratio = pt_corr[keep] / np.maximum(jets[keep, 1], 1e-9)
    out[:, 0] = jets[keep, 0] * ratio   # scale E by the pt-reduction ratio
    out[:, 1] = pt_corr[keep]
    return out[np.argsort(-out[:, 1])] if len(out) else out


def analyze_jets(files, R=0.4, min_pt=10.0, eta_acc=3.5, match_dr=0.3, max_events=0,
                 pileup_subtract=False, leading_n=0):
    """Core jet analysis. Returns dict with summary stats + raw arrays (for plotting)."""
    eresp, ptresp, jpt, jeta = [], [], [], []
    nrecoj, ntruthj, rho_list = [], [], []
    sumE_pfo, sumE_vis = [], []
    nev = 0
    for fn in files:
        try:
            t = uproot.open(fn)["events"]
        except Exception as e:
            print(f"[skip] {fn}: {e}"); continue
        a = t.arrays(PFO_BRANCHES, library="np")
        n = len(a["GaudiPandoraPFOs/GaudiPandoraPFOs.energy"])
        for i in range(n):
            if max_events and nev >= max_events:
                break
            nev += 1
            ppx = a["GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.x"][i]
            ppy = a["GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.y"][i]
            ppz = a["GaudiPandoraPFOs/GaudiPandoraPFOs.momentum.z"][i]
            pE = a["GaudiPandoraPFOs/GaudiPandoraPFOs.energy"][i]
            mpdg = a["MCParticles/MCParticles.PDG"][i]
            mgs = a["MCParticles/MCParticles.generatorStatus"][i]
            mx = a["MCParticles/MCParticles.momentum.x"][i]; my = a["MCParticles/MCParticles.momentum.y"][i]
            mz = a["MCParticles/MCParticles.momentum.z"][i]; mm = a["MCParticles/MCParticles.mass"][i]
            mp = np.sqrt(mx**2 + my**2 + mz**2); mE = np.sqrt(mp**2 + mm**2)
            meta = np.arctanh(np.clip(mz / np.where(mp > 0, mp, 1), -0.999999, 0.999999))
            vis = (mgs == 1) & (~np.isin(np.abs(mpdg), list(NU))) & (np.abs(meta) < eta_acc)
            sumE_pfo.append(float(np.sum(pE))); sumE_vis.append(float(np.sum(mE[vis])))

            # With pileup subtraction we cluster down to a low pt floor, subtract the rho*area
            # pedestal from BOTH reco and truth jets (in-time pileup is not separable at truth
            # level, so the truth jet also carries ~rho*area of pileup-in-cone), then re-apply
            # the pt threshold on the CORRECTED pt. Without it, the legacy min_pt clustering.
            clpt = 5.0 if pileup_subtract else min_pt
            rj = cluster_jets(ppx, ppy, ppz, pE, R, clpt)
            tj = cluster_jets(mx[vis], my[vis], mz[vis], mE[vis], R, clpt)

            if pileup_subtract:
                ppt = np.hypot(ppx, ppy)
                pp = np.sqrt(ppx**2 + ppy**2 + ppz**2)
                peta = np.arctanh(np.clip(ppz / np.where(pp > 0, pp, 1), -0.999999, 0.999999))
                pphi = np.arctan2(ppy, ppx)
                rho_reco = grid_rho(peta, pphi, ppt, eta_acc)
                tpt = np.hypot(mx[vis], my[vis])
                tphi = np.arctan2(my[vis], mx[vis])
                rho_truth = grid_rho(meta[vis], tphi, tpt, eta_acc)
                rho_list.append(rho_reco)
                rj = subtract_pileup(rj, rho_reco, R)
                tj = subtract_pileup(tj, rho_truth, R)
                rj = rj[rj[:, 1] > min_pt] if len(rj) else rj   # threshold on corrected pt
                tj = tj[tj[:, 1] > min_pt] if len(tj) else tj

            rj = rj[np.abs(rj[:, 2]) < eta_acc] if len(rj) else rj
            tj = tj[np.abs(tj[:, 2]) < eta_acc] if len(tj) else tj
            if leading_n and len(tj) > leading_n:
                tj = tj[:leading_n]   # already pt-sorted desc
            nrecoj.append(len(rj)); ntruthj.append(len(tj))
            for (tE, tpt, te, tp) in tj:
                if len(rj) == 0:
                    continue
                dr = np.sqrt((rj[:, 2] - te)**2 + dphi(rj[:, 3], tp)**2)
                k = int(np.argmin(dr))
                if dr[k] < match_dr:
                    eresp.append(rj[k, 0] / max(tE, 1e-9))
                    ptresp.append(rj[k, 1] / max(tpt, 1e-9))
                    jpt.append(tpt); jeta.append(te)

    eresp = np.array(eresp); ptresp = np.array(ptresp)
    jpt = np.array(jpt); jeta = np.array(jeta)
    efrac = np.array(sumE_pfo) / np.maximum(np.array(sumE_vis), 1e-9)

    def stats(x):
        if len(x) == 0:
            return dict(n=0)
        q1, med, q3 = np.percentile(x, [25, 50, 75])
        return dict(n=int(len(x)), median=float(med), mean=float(np.mean(x)),
                    iqr=float(q3 - q1), iqr_over_med=float((q3 - q1) / max(med, 1e-9)))

    summary = dict(
        files=len(files), events=nev, R=R, min_jet_pt=min_pt, eta_acc=eta_acc,
        match_dr=match_dr, pileup_subtract=bool(pileup_subtract), leading_n=int(leading_n),
        n_matched_jets=int(len(eresp)),
        jet_E_response=stats(eresp), jet_pt_response=stats(ptresp),
        mean_nreco_jets=float(np.mean(nrecoj)) if nrecoj else 0,
        mean_ntruth_jets=float(np.mean(ntruthj)) if ntruthj else 0,
        mean_rho_gev=float(np.mean(rho_list)) if rho_list else 0.0,
        event_sumE_pfo_over_vis=stats(efrac),
    )
    arrays = dict(eresp=eresp, ptresp=ptresp, jpt=jpt, jeta=jeta,
                  nrecoj=np.array(nrecoj), ntruthj=np.array(ntruthj),
                  sumE_frac=efrac, rho=np.array(rho_list))
    return dict(summary=summary, arrays=arrays)


def make_figure(summary, arrays, out_prefix, label="", R=0.4):
    eresp = arrays["eresp"]; jpt = arrays["jpt"]
    nrecoj = arrays["nrecoj"]; ntruthj = arrays["ntruthj"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    if len(eresp):
        axes[0].hist(eresp, bins=np.linspace(0, 2, 60), color="#3182ce", alpha=0.85)
        s = summary["jet_E_response"]
        axes[0].axvline(s["median"], color="k", ls="--",
                        label=f"median={s['median']:.3f}\nIQR/med={s['iqr_over_med']:.3f}\nn={s['n']}")
        axes[0].axvline(1.0, color="green", ls=":", alpha=0.7)
        axes[0].set_xlabel("jet $E_{reco}/E_{truth}$"); axes[0].set_ylabel("matched jets")
        axes[0].set_title("Jet energy response"); axes[0].legend(fontsize=9)
        if len(jpt):
            bins = np.array([10, 20, 40, 70, 120, 200, 400, 1000])
            idx = np.digitize(jpt, bins)
            bx, bmed, blo, bhi = [], [], [], []
            for bidx in range(1, len(bins)):
                m = idx == bidx
                if np.sum(m) >= 5:
                    q1, md, q3 = np.percentile(eresp[m], [25, 50, 75])
                    bx.append(np.sqrt(bins[bidx - 1] * bins[bidx])); bmed.append(md); blo.append(md - q1); bhi.append(q3 - md)
            if bx:
                axes[1].errorbar(bx, bmed, yerr=[blo, bhi], fmt="o-", color="#dd6b20", capsize=3)
            axes[1].axhline(1.0, color="green", ls=":", alpha=0.7)
            axes[1].set_xscale("log"); axes[1].set_xlabel("truth jet $p_T$ [GeV]")
            axes[1].set_ylabel("median $E_{reco}/E_{truth}$"); axes[1].set_title("Jet response vs $p_T$")
            axes[1].grid(alpha=0.2)
    if len(nrecoj):
        mxj = int(max(nrecoj.max(), ntruthj.max())) + 1
        axes[2].hist(ntruthj, bins=range(0, mxj + 1), alpha=0.5, label=f"truth (mean {ntruthj.mean():.1f})", color="#718096")
        axes[2].hist(nrecoj, bins=range(0, mxj + 1), alpha=0.5, label=f"reco (mean {nrecoj.mean():.1f})", color="#3182ce")
        axes[2].set_xlabel("# jets / event"); axes[2].set_ylabel("events")
        axes[2].set_title("Jet multiplicity"); axes[2].legend(fontsize=9)
    fig.suptitle(f"ODD Pandora PF — jet validation (anti-$k_T$ R={R})" + (f" — {label}" if label else ""),
                 fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_prefix + "_response.png", dpi=140)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reco", nargs="+", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--R", type=float, default=0.4)
    ap.add_argument("--min-jet-pt", type=float, default=10.0)
    ap.add_argument("--eta-acc", type=float, default=3.5)
    ap.add_argument("--match-dr", type=float, default=0.3)
    ap.add_argument("--label", default="")
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--pileup-subtract", action="store_true")
    ap.add_argument("--leading-n", type=int, default=0)
    ap.add_argument("--dump", action="store_true", help="also save raw arrays to <out-prefix>_arrays.npz")
    args = ap.parse_args()

    files = []
    for f in args.reco:
        files.extend(sorted(glob.glob(f)))

    res = analyze_jets(files, R=args.R, min_pt=args.min_jet_pt, eta_acc=args.eta_acc,
                       match_dr=args.match_dr, max_events=args.max_events,
                       pileup_subtract=args.pileup_subtract, leading_n=args.leading_n)
    summary = res["summary"]; summary["label"] = args.label
    with open(args.out_prefix + "_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    if args.dump:
        np.savez_compressed(args.out_prefix + "_arrays.npz", **res["arrays"])
    make_figure(summary, res["arrays"], args.out_prefix, label=args.label, R=args.R)
    print(f"[jet_analysis] {summary['events']} events, {summary['n_matched_jets']} matched jets "
          f"-> {args.out_prefix}_response.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
