# Pandora settings tuning appendix (μ=200 speed/physics study)

This documents the PandoraSettingsCLD XML variants explored while optimizing ODD particle flow at
⟨μ⟩=200 (May–June 2026). Only the curated set is committed in `k4ODD/options/`; the experimental
variants below are **not** committed (preserved in the pre-sprint snapshot tarball) because the shipped
solution is **algorithmic, not parametric**: the optimized LCContent build
(`OpenDataDetector/LCContent @ colliderml/v03-02-00-opt`) reaches **60.2 → 10.6 min/event (5.66×)
byte-identically** with the *full* `PandoraSettingsCLD.xml`, spending none of the physics budget.
Full measurements: `doc/OPTIMIZATION_LOG.md`.

## Committed set

| file | use |
|---|---|
| `PandoraSettingsCLD.xml` | **Production.** Full CLD charged-PF chain (all reclustering blocks, NMaxPasses=200). Pair with the optimized LCContent for speed. |
| `PandoraSettingsCLD_balanced.xml` | Reduced reclustering (subset of ConeClustering re-passes). ~1.5%-class physics deltas; use only if wall time matters more than the last % at very high pileup. |
| `PandoraSettingsCLD_fast.xml` | Aggressively reduced association/reclustering. Several-% physics deltas; debugging/throughput exploration only. |
| `PandoraSettingsMinimalNoMonitor.xml` | Calo-only neutral PF, no monitoring output. CI digitisation checks. |
| `PandoraSettingsTracks.xml` | Tracks-only stub for debugging track creators. |

## Experimental variants (not committed; measurements at μ=200, single ttbar event, vs stock 3614 s)

| variant | knob | wall | physics delta | verdict |
|---|---|---:|---|---|
| `_pass50` | `<NMaxPasses>50</NMaxPasses>` on NeutralFragmentRemoval | 485 s (8.1 min, with cache lib) | **+2.47% ΣE, +13.9% neutron count, +8.5% 1-event jet response** — un-absorbed neutral fragments double-count energy | exceeds 3% budget; rejected |
| `_cut300` | ContactCutMaxDistance 500→300 mm | ~0 NFR gain (helps MFR only) | ~+0.5% ΣE | useless for the dominant term; rejected |
| `_norecluster`, `_norecluster_true` | drop reclustering blocks | large | charged/neutral separation degrades | ceiling probes only |
| `_noassoc` | drop topological association chain | large | unacceptable | budget probe only |
| `_noSC` | software compensation off | — | response slope returns | diagnostic only |
| `_t3chi`, `_t3halt` | ChiToAttemptReclustering / halt-χ² tightening | modest | trigger-count reduction probes | superseded by algorithmic fix |
| `_aggr`, `_aggrdrop` | combined aggressive | large | well over budget | rejected |

## Key findings (why parameter tuning lost to algorithmics)

1. **ContactCutMaxDistance cannot prune NeutralFragmentRemoval** — large neutral clusters keep small
   bounding-sphere separations at μ=200, so the spatial cut removes ~0% of NFR pairs.
2. **NMaxPasses is a strong lever but buys speed with physics**: every dropped pass leaves a neutral
   fragment un-absorbed → energy double-counted against charged showers (+2.5% ΣE at pass50).
3. **A ~300 s primary-clustering floor** (ConeClustering + CaloHitPrep + SoftClusterMerging) sits under
   everything; settings tuning cannot reach <10 min with margin.
4. The shipped answer — sorted-sweep nearest-neighbour in `ClusterContact` + cross-pass contact caching
   in Main/NeutralFragmentRemoval — does **all the same merges** (byte-identical, 0.00% on
   N/ΣE/Σ|p|/composition) at 5.66×. Steady-state multi-event throughput: 22/44/80/156 events/node-hour
   at P=8/16/32/64 on one 128-core EPYC 7763.
