#!/usr/bin/env python3
"""Physics-metrics comparison of two reco outputs (for the ConeClustering rewrite, where byte-identical is
NOT required but all metrics must agree within a small percentage). Compares PFO/cluster multiplicity,
energy, momentum and per-type composition, aggregated over events and as per-event means."""
import sys
from podio import root_io

PFO = ["GaudiPandoraPFOs", "PandoraPFOs"]
CLU = ["GaudiPandoraClusters", "PandoraClusters"]


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


def load(fn):
    r = root_io.Reader(fn)
    ev = []
    for frame in r.get("events"):
        pfos = _first(frame, PFO)
        clus = _first(frame, CLU)
        d = {"npfo": 0, "epfo": 0.0, "ppfo": 0.0, "nclu": 0, "eclu": 0.0, "types": {}}
        if pfos is not None:
            for p in pfos:
                d["npfo"] += 1
                d["epfo"] += float(p.getEnergy())
                m = p.getMomentum()
                d["ppfo"] += (m.x*m.x + m.y*m.y + m.z*m.z) ** 0.5
                t = _pid(p)
                d["types"][t] = d["types"].get(t, 0) + 1
        if clus is not None:
            for c in clus:
                d["nclu"] += 1
                d["eclu"] += float(c.getEnergy())
        ev.append(d)
    return ev


def agg(ev, key):
    return sum(e[key] for e in ev)


def reldiff(a, b):
    return 0.0 if (a == 0 and b == 0) else 100.0 * (b - a) / (a if a else 1)


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0  # percent
    print(f"events: stock={len(a)} opt={len(b)}")
    if len(a) != len(b):
        print("EVENT COUNT DIFFERS"); sys.exit(1)
    rows = []
    for key, label in [("npfo", "N PFO"), ("epfo", "sum E_PFO"), ("ppfo", "sum |p|_PFO"),
                       ("nclu", "N cluster"), ("eclu", "sum E_cluster")]:
        sa, sb = agg(a, key), agg(b, key)
        rows.append((label, sa, sb, reldiff(sa, sb)))
    # per-type PFO composition
    types = set()
    for e in a + b:
        types.update(e["types"].keys())
    worst = 0.0
    print(f"{'metric':<16}{'stock':>14}{'opt':>14}{'rel% ':>9}")
    for label, sa, sb, rd in rows:
        print(f"{label:<16}{sa:>14.3f}{sb:>14.3f}{rd:>+8.2f}%")
        worst = max(worst, abs(rd))
    print("-- PFO type composition --")
    for t in sorted(types):
        ca = sum(e["types"].get(t, 0) for e in a)
        cb = sum(e["types"].get(t, 0) for e in b)
        rd = reldiff(ca, cb)
        print(f"  pdg {t:<6}{ca:>12}{cb:>12}{rd:>+8.2f}%")
        if ca + cb > 20:  # only enforce tolerance on well-populated types
            worst = max(worst, abs(rd))
    print(f"\nworst |rel diff| (well-populated metrics) = {worst:.2f}%   tolerance = {tol:.1f}%")
    if worst <= tol:
        print(f"==> METRICS-EQUIVALENT within {tol:.1f}% ✓"); sys.exit(0)
    print("==> METRICS DIFFER beyond tolerance ✗"); sys.exit(1)


if __name__ == "__main__":
    main()
