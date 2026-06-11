#!/usr/bin/env python3
"""Stage 7 — full validation-suite analyzer (η × E × particle).

Reads one or more metrics jsonl files (each row: particle, energy, eta, charged_primary,
mean_response, median_response, resolution_rms_over_mean, charged_pfo_efficiency,
leading_pid_purity, mean_npfo, pid_hist). Produces the validation plot suite + an acceptance
table. Supports before/after overlay (--before uncalibrated.jsonl --after calibrated.jsonl).

Usage:
    analyze_validation.py --metrics calib_validation.jsonl --outdir testbed/results/validation
    analyze_validation.py --before base.jsonl --after final.jsonl --outdir .../validation
"""
import argparse, json, math, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ORDER = ["gamma", "e-", "mu-", "pi-", "neutron", "kaon0L"]
COL = {"gamma": "tab:orange", "e-": "tab:blue", "mu-": "tab:green",
       "pi-": "tab:red", "neutron": "tab:purple", "kaon0L": "tab:brown"}
ETA_MARK = {0.5: "o", 1.0: "s", 2.0: "^", 2.5: "D"}


def load(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    by = {}
    for r in rows:
        by.setdefault((r["particle"], float(r.get("eta", 0.5))), []).append(r)
    for k in by:
        by[k].sort(key=lambda r: r["energy"])
    return by


def particles_in(by):
    ps = sorted({k[0] for k in by}, key=lambda p: ORDER.index(p) if p in ORDER else 99)
    return ps


def etas_in(by):
    return sorted({k[1] for k in by})


def plot_metric(by, field, ylabel, title, fname, outdir, ylim=None, logy=False, ref1=False,
                charged_only=False):
    plt.figure(figsize=(8, 5.5))
    for p in particles_in(by):
        for eta in etas_in(by):
            recs = by.get((p, eta))
            if not recs:
                continue
            if charged_only and not recs[0].get("charged_primary"):
                continue
            xs = [r["energy"] for r in recs]
            ys = [r.get(field, float("nan")) for r in recs]
            lbl = f"{p} η{eta}" if len(etas_in(by)) > 1 else p
            plt.plot(xs, ys, "-" + ETA_MARK.get(eta, "o"), color=COL.get(p), label=lbl, ms=5, alpha=0.85)
    if ref1:
        plt.axhline(1.0, color="k", ls=":", lw=1)
    plt.xscale("log")
    if logy:
        plt.yscale("log")
    if ylim:
        plt.ylim(*ylim)
    plt.xlabel("True energy [GeV]"); plt.ylabel(ylabel); plt.title(title)
    plt.legend(fontsize=6, ncol=3); plt.grid(alpha=0.3, which="both")
    plt.tight_layout(); plt.savefig(os.path.join(outdir, fname), dpi=120); plt.close()


def acceptance_table(by):
    """Return text table + pass/fail flags."""
    lines = [f"{'particle':8} {'η':>4} {'E':>5} {'resp_mean':>9} {'resp_med':>8} {'res':>6} "
             f"{'chEff':>5} {'pidPur':>6}"]
    worst_resp = 0.0
    for p in particles_in(by):
        for eta in etas_in(by):
            for r in by.get((p, eta), []):
                lines.append(f"{p:8} {eta:4.1f} {r['energy']:5.0f} {r['mean_response']:9.3f} "
                             f"{r['median_response']:8.3f} {r['resolution_rms_over_mean']:6.3f} "
                             f"{r['charged_pfo_efficiency']:5.2f} {r['leading_pid_purity']:6.2f}")
                worst_resp = max(worst_resp, abs(r["median_response"] - 1.0))
    return "\n".join(lines), worst_resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics")
    ap.add_argument("--before")
    ap.add_argument("--after")
    ap.add_argument("--outdir", default="results/validation")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    if args.metrics:
        by = load(args.metrics)
        plot_metric(by, "mean_response", "Response  ΣE_PFO/E_true", "Energy response vs E (mean)",
                    "val_response_mean_vs_E.png", args.outdir, ref1=True)
        plot_metric(by, "median_response", "Median response", "Energy response vs E (median)",
                    "val_response_median_vs_E.png", args.outdir, ref1=True)
        plot_metric(by, "resolution_rms_over_mean", "RMS/mean", "Energy resolution vs E",
                    "val_resolution_vs_E.png", args.outdir, logy=True)
        plot_metric(by, "charged_pfo_efficiency", "charged-PFO efficiency", "Charged efficiency vs E",
                    "val_charged_eff_vs_E.png", args.outdir, ylim=(-0.05, 1.05), charged_only=True)
        plot_metric(by, "leading_pid_purity", "leading-PFO PID purity", "PID purity vs E",
                    "val_pid_purity_vs_E.png", args.outdir, ylim=(-0.05, 1.05))
        tbl, worst = acceptance_table(by)
        print(tbl)
        print(f"\nworst |median_response - 1| across grid = {worst:.3f}")
        with open(os.path.join(args.outdir, "acceptance_table.txt"), "w") as fh:
            fh.write(tbl + f"\n\nworst |median_response-1| = {worst:.3f}\n")

    if args.before and args.after:
        b = load(args.before); a = load(args.after)
        # before/after median response overlay, one panel per particle
        ps = particles_in(a)
        n = len(ps)
        if n == 0:
            print("before/after: no 'after' data — skipping overlay")
            print("validation plots ->", args.outdir)
            return
        fig, axes = plt.subplots(2, (n + 1) // 2, figsize=(4 * ((n + 1) // 2), 8), squeeze=False)
        for i, p in enumerate(ps):
            ax = axes[i // ((n + 1) // 2)][i % ((n + 1) // 2)]
            for eta in etas_in(a):
                ra = a.get((p, eta)); rb = b.get((p, eta))
                if ra:
                    ax.plot([r["energy"] for r in ra], [r["median_response"] for r in ra],
                            "-o", color="tab:green", ms=4, label=f"after η{eta}")
                if rb:
                    ax.plot([r["energy"] for r in rb], [r["median_response"] for r in rb],
                            "--x", color="tab:red", ms=4, label=f"before η{eta}")
            ax.axhline(1.0, color="k", ls=":", lw=1)
            ax.set_xscale("log"); ax.set_title(p); ax.set_xlabel("E [GeV]"); ax.set_ylabel("median resp")
            ax.grid(alpha=0.3); ax.legend(fontsize=6)
        fig.suptitle("Median response before (uncalibrated) vs after (calibrated)")
        fig.tight_layout(); fig.savefig(os.path.join(args.outdir, "val_before_after_response.png"), dpi=120)
        plt.close(fig)
        print("wrote before/after overlay")

    print("validation plots ->", args.outdir)


if __name__ == "__main__":
    main()
