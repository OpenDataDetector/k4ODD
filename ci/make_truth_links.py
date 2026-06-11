#!/usr/bin/env python3
"""Add PFO<->MC truth-link collections to an ODD Pandora reco file, for k4DetectorPerformance
(PFONTupleWriter) and any other consumer of CLD-style RecoMCTruthLink collections.

The ODD Gaudi chain does not run the Marlin RecoMCTruthLinker, so reco files carry only the
calo digi<->sim links (digiRelationCaloHit). This post-step derives the PFO-level links:

  RecoMCTruthLink   (reco -> mc): weight encodes, per MC particle, the fraction OF THE PFO
                    (cluster energy / track hits) that came from it.
  MCTruthRecoLink   (mc -> reco): weight encodes, per PFO, the fraction OF THE MC PARTICLE's
                    deposits (calo energy / tracker sim hits) that ended up in it.
  SiTracksMCTruthLink (track -> mc): passed through if present (written by the ACTS track
                    conversion, which owns the measurement->particle truth; edm4hep ActsTracks
                    carry no hit references so it CANNOT be derived here), else written empty.

Weights use the MarlinUtil encoding PFONTupleWriter decodes:
  weight = int(trackwgt*1000)%10000 + int(clusterwgt*1000)*10000

Cluster weights walk PFO -> clusters -> CalorimeterHits -> digiRelationCaloHit ->
SimCalorimeterHit -> contributions -> MCParticle, with energies from the contributions.
MC particles are backtracked to their generator-status!=0 ancestor so secondaries' deposits
count toward the primary (simple parent-walk; sufficient for single-particle and jet eval).

Usage (inside a key4hep env):
  python3 make_truth_links.py -i reco.root -o reco_links.root \
      [--pfos GaudiPandoraPFOs] [--calorel digiRelationCaloHit] [--tracklinks SiTracksMCTruthLink]
"""

import argparse
import sys

from podio import root_io
import podio
import edm4hep


def oid(obj):
    o = obj.getObjectID()
    return (o.collectionID, o.index)


def encode_weight(trackwgt, clusterwgt):
    tw = max(0.0, min(trackwgt, 0.999))
    cw = max(0.0, min(clusterwgt, 0.999))
    return float(int(tw * 1000) % 10000 + int(cw * 1000) * 10000)


def backtrack(mcp):
    """Walk to the generator-level ancestor (genStatus != 0), so secondaries count
    toward the particle the evaluation loops over."""
    seen = 0
    while int(mcp.getGeneratorStatus()) == 0 and mcp.getParents().size() > 0 and seen < 64:
        mcp = mcp.getParents()[0]
        seen += 1
    return mcp


def process_event(frame, args):
    pfos = frame.get(args.pfos)
    mcps = frame.get("MCParticles")

    # digi CalorimeterHit -> SimCalorimeterHit map
    hit2sim = {}
    try:
        for link in frame.get(args.calorel):
            hit2sim[oid(link.getFrom())] = link.getTo()
    except Exception:
        pass

    # MC keying: backtracked MCParticle by ObjectID, kept as handle for link targets
    # E_pc[(pfo_i, mc_key)] = calo energy in pfo's clusters contributed by mc
    # E_pfo[pfo_i] = total digi energy of the pfo's cluster hits
    # E_mc[mc_key] = total digi-linked calo energy contributed by mc anywhere in the event
    E_pc, E_pfo, E_mc = {}, {}, {}
    mc_handle = {}

    def contribs_of(sim_hit):
        for c in sim_hit.getContributions():
            anc = backtrack(c.getParticle())
            k = oid(anc)
            mc_handle.setdefault(k, anc)
            yield k, float(c.getEnergy())

    # total per-MC calo energy: every digi-linked sim hit in the event
    for k_hit, sim in hit2sim.items():
        for k, e in contribs_of(sim):
            E_mc[k] = E_mc.get(k, 0.0) + e

    for ip, pfo in enumerate(pfos):
        tot = 0.0
        for clu in pfo.getClusters():
            for hit in clu.getHits():
                tot += float(hit.getEnergy())
                sim = hit2sim.get(oid(hit))
                if sim is None:
                    continue
                for k, e in contribs_of(sim):
                    E_pc[(ip, k)] = E_pc.get((ip, k), 0.0) + e
        E_pfo[ip] = tot

    # track weights from the (ACTS-provided) track->MC links, aggregated per PFO
    # reco->mc: fraction of the PFO's track hits from mc (single-track PFOs: the link weight)
    # mc->reco: fraction of the mc's sim hits captured (we reuse the same weight; the ACTS
    #           converter writes purity-style weights, refine when both fractions are exported)
    trk2mc = {}  # track oid -> list[(mc_key, weight)]
    if args.tracklinks:
        try:
            for link in frame.get(args.tracklinks):
                anc = backtrack(link.getTo())
                k = oid(anc)
                mc_handle.setdefault(k, anc)
                trk2mc.setdefault(oid(link.getFrom()), []).append((k, float(link.getWeight())))
        except Exception:
            pass

    T_pc = {}  # (pfo_i, mc_key) -> track weight (max over the pfo's tracks)
    for ip, pfo in enumerate(pfos):
        for trk in pfo.getTracks():
            for k, w in trk2mc.get(oid(trk), []):
                T_pc[(ip, k)] = max(T_pc.get((ip, k), 0.0), w)

    reco2mc = edm4hep.RecoMCParticleLinkCollection()
    mc2reco = edm4hep.RecoMCParticleLinkCollection()

    pairs = sorted(set(E_pc) | set(T_pc))
    for ip, k in pairs:
        pfo = pfos[ip]
        mc = mc_handle[k]
        ec = E_pc.get((ip, k), 0.0)
        tw = T_pc.get((ip, k), 0.0)

        cw_reco = ec / E_pfo[ip] if E_pfo.get(ip, 0.0) > 0 else 0.0
        cw_mc = ec / E_mc[k] if E_mc.get(k, 0.0) > 0 else 0.0

        l1 = reco2mc.create()
        l1.setFrom(pfo)
        l1.setTo(mc)
        l1.setWeight(encode_weight(tw, cw_reco))

        l2 = mc2reco.create()
        l2.setFrom(pfo)
        l2.setTo(mc)
        l2.setWeight(encode_weight(tw, cw_mc))

    n_links = len(pairs)
    return reco2mc, mc2reco, n_links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--pfos", default="GaudiPandoraPFOs")
    ap.add_argument("--calorel", default="digiRelationCaloHit")
    ap.add_argument("--tracks", default="", help="track collection to mirror into SiTracks links (e.g. ActsTracks)")
    ap.add_argument("--tracklinks", default="", help="existing TrackMCParticleLink collection to aggregate (from ACTS conversion)")
    ap.add_argument("--max-events", type=int, default=-1)
    args = ap.parse_args()

    reader = root_io.Reader(args.input)
    writer = root_io.Writer(args.output)

    # carry non-event categories (metadata etc.) so downstream podio readers stay happy
    for cat in reader.categories:
        if cat == "events":
            continue
        for fr in reader.get(cat):
            writer.write_frame(fr, cat)

    n_ev = 0
    n_links_tot = 0
    for fr in reader.get("events"):
        if 0 <= args.max_events <= n_ev:
            break
        reco2mc, mc2reco, n_links = process_event(fr, args)
        existing = list(fr.getAvailableCollections())
        fr.put(reco2mc, "RecoMCTruthLink")
        fr.put(mc2reco, "MCTruthRecoLink")
        if args.tracklinks == "" or args.tracklinks not in existing:
            # PFONTupleWriter requires the collection to exist: write it (empty) if absent
            fr.put(edm4hep.TrackMCParticleLinkCollection(), "SiTracksMCTruthLink")
        writer.write_frame(fr, "events")
        n_ev += 1
        n_links_tot += n_links

    if hasattr(writer, "close"):
        writer.close()
    else:
        del writer  # podio Writer finishes the file on destruction
    print(f"wrote {args.output}: {n_ev} events, {n_links_tot} PFO<->MC links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
