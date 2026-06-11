# ODD Calorimeter + Particle-Flow Calibration — Journal

Goal: fully calibrated digitisation + particle flow, all particle types, full detector
(η) and energy spectrum. Staged PandoraPFA bootstrap. Plan:
`~/.claude/plans/peppy-rolling-hartmanis.md`. Deliverable: Beamer/Tectonic deck.

Compute model: heavy sim/validation on SLURM `sbatch`; fast reco-iteration on interactive
`salloc` via `srun --overlap`. All reco through CLD charged-PF chain (`PandoraSettingsCLD.xml`),
ACTS tracks for charged. Stack: shifter atlas-grid-almalinux9 + LCG_107 + key4hep.

Baseline (pre-calibration, ideal digi, η=0.5, from the first sweep):
- EM scale ~right (γ resp 0.98–1.04); **hadronic under-calibrated** (n 0.56→0.78, K_L 0.52→0.82,
  rising with E → non-compensation). μ perfect (resp 1.00, res 1%). e⁻/π⁻ track-dominated resp ~1.
- PID: γ/n confusion worsens with E (γ purity 0.47 @100 GeV); e⁻ PID ceiling (>50 GeV); low-E
  neutral hadrons largely lost; K_L→2112 (correct, metric artifact).

---

## Stage 0 — calibration iteration infrastructure

### 0a. Env-overridable calo constants in `ODDreconstruction.py`  ✅
Added `_env_float/_env_int/_env_floats` helpers; wired 24 knobs (defaults reproduce prior values):
- Digi: `K4ODD_CALIBR_ECAL`, `K4ODD_CALIBR_HCAL_{BARREL,ENDCAP,OTHER}`,
  `K4ODD_{ECAL,HCAL}_ENDCAP_CORR`, `K4ODD_{ECAL,HCAL}_REALISTIC_DIGI`,
  `K4ODD_{ECAL,HCAL}_NOISE_MIPS`, `K4ODD_{ECAL,HCAL}_MISCAL`, `K4ODD_{ECAL,HCAL}_DEADCELL_RATE`.
- Pandora: `K4ODD_{EM,HAD}_{CONST,STOCH}`, `K4ODD_{ECAL,HCAL}_EM_SCALE`,
  `K4ODD_ECAL_HAD_SCALE_{BARREL,ENDCAP}`, `K4ODD_HCAL_HAD_SCALE`, `K4ODD_SOFTCOMP_WEIGHTS`.
- `python3 -m py_compile` clean. Two scale layers exist: digi (`CalibrECAL`=37.52,
  `CalibrHCALBarrel`=45.99) and Pandora (`ECalToHadGeVCalBarrel`=1.115, `HCalToHadGeVCal`=1.006,
  `ECalToEMGeVCal`=1.018). Hadronic fix will go on the Pandora HAD-scale layer (the designed knob).

### 0b. Sim/reco split + iteration scripts  (in progress)
- `reco_iter.sh`: reco-only on a cached sim, forwarding all calibration env knobs into shifter.
- `build_sim_cache.sh`: sbatch array building sim_with_tracks.root once per (particle,E,η).

### 0c. This journal.  ✅

### 0b validated (smoke, neutron E10 η0.5, 20 ev)  ✅
- `SIM_ONLY=1` → sim_with_tracks.root produced, reco skipped ✓.
- `reco_iter.sh` forwards knobs into shifter ✓; `K4ODD_HCAL_HAD_SCALE=1.30` moved neutron
  response 0.719→0.772.
- **Finding**: HCAL-only HAD-scale knob is a WEAK lever (~7% per 30%) because hadron energy
  splits ECAL/HCAL and SC partially counteracts. → Stage 2 will calibrate hadronic scale via the
  digi `CalibrHCAL` (scales all HCAL hit GeV, strong lever) and/or combined Pandora HAD scale.
- Stage 0 COMPLETE.

---
## Stage 1 — sim cache (Geant4+ACTS, sbatch)
Grid: 6 particles {γ,e-,μ-,π-,n,K_L} × 9 E {0.5,1,2,5,10,20,50,100,200} × 4 η {0.5,1.0,2.0,2.5}
= 216 buckets × 500 ev, SIM_ONLY. Reusable for calibration (reco-iter) AND final validation.
Calibration-critical (do first): neutral η=0.5 = γ idx 0,4,...,32; n idx 144..176; K_L idx 180..212.

---
## Stage 2 — HAD-scale lever study (on cached smoke neutron E10, before sims land)
Neutron E10 η0.5 response (median), nominal 0.716:
| knob change | resp_med |
|---|---|
| nominal | 0.716 |
| digi CalibrHCALBarrel ×1.4 | 0.745 |
| digi CalibrHCALBarrel ×1.6 | 0.748 |
| **ECalToHadGeVCalBarrel ×1.4 + digi-HCAL ×1.4** | **0.969** |

→ **Dominant hadronic lever = `ECalToHadGeVCalibrationBarrel`** (Pandora ECAL-hadronic calib):
hadrons deposit a large fraction in ODD's deep ECAL, reconstructed via the ECAL→Had calibration.
HCAL knobs alone are weak (~+3% per ×1.4). **Stage-2 HAD recipe**: scale all three Pandora HAD
constants (`ECalToHadGeVCalibration{Barrel,EndCap}`, `HCalToHadGeVCalibration`) by a common factor;
response is ~linear in it (dresp/dfactor ≈ 0.63 at 10 GeV). Calibrate at a high reference E
(~50 GeV, SC-insensitive) → response 1.0; SC (Stage 3) flattens the low-E deficit.
EM recipe: `ECalToEMGeVCalibration` from γ (small, ~×1.02). Both via 2-point linear solve.

---
## Stage log (append per action)
- sim cache 53574137 submitted (216×500ev, %64). Queued (shared qos). Building Stage 2/3 code while waiting.
- Stage 2 driver `calibrate_scale.py` written (2-point linear solve for EM + HAD scale factors → calib_constants.env).
- Stage 3 SC: investigating LCContent `LCSoftwareCompensation` form. Expected CALICE form
  E_SC = Σ_i E_i·[p1+p2·exp(p3·ρ_i)], p_k=β_k1+β_k2·E+β_k3·E² (9 weights). Needs per-hit energy
  density ρ_i=E_i/V_cell. Decision pending form check: full re-fit (needs cell-volume plumbing) vs
  verify/keep CLD weights + quantify residual non-compensation slope (defensible fallback,
  full PandoraAnalysis SC re-derivation scoped as follow-up).
- DECISION (SC): shared-qos array stuck pending + cvmfs LCContent find timed out. For a defensible
  overnight run: Stage 3 = VALIDATE+RETAIN CLD SC weights (SC-on vs SC-off response-flatness/resolution),
  quantify residual non-compensation slope; full ODD-specific CALICE SC weight refit scoped as
  follow-up (needs per-hit cell-volume density + PandoraAnalysis training framework).
- EFFICIENCY PIVOT: shared-qos array slow to schedule → built `build_calib_quick.sh` to generate the
  calibration subset (6 part × 9 E × η0.5, 200 ev) on the interactive node (53568479) in parallel →
  `testbed/runs/calib_quick/`. Stages 2-5 calibrate on calib_quick (barrel); full η grid (calib_grid,
  500ev sbatch 53574137) for Stage 7 validation.
- STAGED TOOLS (no-compute, ready): `calibrate_scale.py` (Stage 2), `analyze_validation.py` (Stage 7
  η×E suite + before/after), `collect_metrics.sh` (reco+metrics over a cached grid under any constants).
- Stage 3 input ready: `PandoraSettingsCLD_noSC.xml` (SC plugin commented) for SC-on-vs-off comparison.
- Stage 8 DE-RISKED: `testbed/deck/calibration.tex` Beamer scaffold (Madrid theme, \IfFileExists-guarded
  figs, \detokenize for pending-fig names) BUILDS via tectonic → calibration.pdf (71 KB). Fill with real
  plots/numbers at Stage 8. tectonic on PATH (~/.pixi/bin), fetches CTAN packages over network.
- Stage-2 watcher armed (fires when γ@10/50 + n/K_L@50 cached sims ready → run calibrate_scale.py).
  Sims building: calib_quick 8/54, calib_grid 5/216.
- calib_grid sbatch STARVED on shared qos (1/216 running — fairshare). Pivoted full-η grid to
  interactive: node1 53568479 builds η0.5 (calib_quick), node2 53575258 (nid004186) builds
  η∈{1.0,2.0,2.5} (200ev each) → testbed/runs/calib_quick. Both nodes saturated with sims.
- LESSON: run calibration recos AFTER a node frees (sims-first). EM 2-point validation failed on
  contention (overlap recos timed out while node1 ran 20 ddsim). Stage 2 will run on the freed
  node1 once its η0.5 build_calib_quick driver exits (~14:25). Code is fine; pure scheduling.
- QOS LIMIT: interactive qos caps 2 concurrent jobs; the 216-task calib_grid sbatch also ate the
  submit limit → CANCELLED 53574137 (starved 7/216). Full η grid now via interactive calib_quick
  (200ev). Stage 7 validation stats = 200ev (defensible; noted in deck).
- Stage 2 EXECUTING autonomously: `stage2_driver.sh` (/tmp/stage2.log) waits for an interactive slot
  (node1 expires ~14:34), allocates a fresh node, runs calibrate_scale.py (γ@10 EM, n/K_L@50 HAD) →
  calib_constants_ideal.env, confirms response→1. 3/4 barrel calib sims ready; HAD uses neutron@50.
- Stage 6b DONE: LCElectronId already loosened to the LCContent-3.2.0 limit by earlier tuning
  (MaxResidualEOverP=1.0, MaxProfileDiscrepancy=1.0, ProfileDiscrepancyForAutoId=1.0). No separate
  energy ceiling exists in this version; residual high-E e-PID drop is intrinsic brems (E/p) — scoped.
- Stage 5+7 AUTOMATED: `pipeline_stages.sh <node>` (verified) chains realistic-digi recalibration
  (calibrate_scale --extra-env REALISTIC_DIGI) → 3-pass validation (uncalibrated/ideal/realistic over
  the cached grid) → analyze_validation plots+acceptance. SC(3)+resolution(4) derived in analysis.
  The 14:55 wakeup launches it on stage2's node once calib_constants_ideal.env exists.
- ORCHESTRATION STATE (~14:30): node1 53568479 expires ~14:32 (η0.5 build 45/54); stage2_driver
  waiting for the freed slot → will allocate node3, run Stage 2; node2 53575258 building other-η
  (32 done). Pipeline auto-runs after. Stage 8 deck = fill constants_table + rebuild tectonic.
- CONSOLIDATED to ONE end-to-end driver `run_all_stages.sh <node>` (task br7gcm7dl) running on
  node 53576479 (reuses the idle node stage2_driver allocated; respects 2-job qos cap). Steps
  through Stages 2→8 autonomously, resumable (skip-if-output-exists), self-healing node realloc,
  bounded sim waits. Produces: calib_constants_{ideal,real}.env, val_{base,ideal,real}.jsonl,
  validation/*.png, testbed/deck/calibration.pdf. Also wrote `gen_constants_table.py` (Stage 8
  before/after table). Notifies on completion (~1.5-2h). Grid at launch: η0.5 46/54, total 79.
- RUN 1 (br7gcm7dl) FAILED — every reco errored "file does not exist": the BUG was reco_iter.sh
  doing `cd k4ODD` before k4run, so RELATIVE input paths (passed by run_all_stages/collect_metrics)
  resolved to k4ODD/testbed/... Fix: reco_iter.sh now ABSOLUTIZES IN/OUT before the shifter cd
  (same bug class as the earlier validation-command slip). Also guarded analyze_validation against
  empty 'after' data. Moved stale factor-1.0 constants + empty jsonls to /tmp/stale_calib.
  Verified the fix: a manual reco_iter on a calib_quick sim now "Terminated successfully".
- RUN 2 (buze51bmx) relaunched on node 53576479 with the fix; grid 95 sims and growing.

## ★ STAGE 2 + 5 CALIBRATED (RUN 2, real data) ★
Ideal digi (apply_realistic_digi=0):
- EM factor **1.0127** (γ resp 0.989 @factor1.0 → solved to 1.0; EM was ~right).
- HAD factor **1.3847** (n 0.762→0.983, K_L 0.791→1.035 @factor1.4, ref 50 GeV; solved 1.385).
- → ECAL_EM=1.031, ECAL_HAD_{bar,end}=1.544, HCAL_HAD=1.392 (calib_constants_ideal.env).
Realistic digi (ECAL=1, HCAL=2): EM factor 1.0127, HAD factor 1.3848 — **nearly identical to ideal**
  (SiPM saturation negligible for ≥GeV showers spread over many cells) → calib_constants_real.env.
Interpretation: hadronic was ~24-28% low (non-compensation), fixed by the ECAL-HAD-dominated scale;
EM was within ~1%. Confirms the earlier sweep diagnosis quantitatively.
Stage 7 validation (3-pass before/after) + deck now running in buze51bmx.

## Stage 7 (RUN 2) — in progress, real data
- base pass DONE (val_base.jsonl, uncalibrated, 100 ev/bucket); ideal pass running.
- FINDING (endcap tracking): charged_pfo_efficiency at η=2.0 ≈ 0 for e- (reco as γ/n only,
  pid_hist has no 11/-211) — ACTS track not used at η=2.0. η≤1.0 fine (e- chEff 0.83-0.98).
  → charged PF validated barrel+transition (η≤1.0); endcap (η=2.0) charged tracking is a gap
  to investigate (seeding/CKF acceptance or track-state at high η). Note in deck/limitations.
- EM resolution already good in baseline (e-/γ res ~4-10% at 10-100 GeV); low-E (0.5-1 GeV)
  noisy as expected. After-calibration (val_ideal) numbers pending pass completion.

## ★★ RUN 2 COMPLETE — CALIBRATED + VALIDATED (16:32) ★★
Deliverables: calib_constants_{ideal,real}.env; val_{base,ideal,real}.jsonl (130/141/149 rows);
testbed/results/validation/*.png (6 plots); testbed/deck/calibration.pdf (950 KiB, real plots+table).
Calibrated scale: EM ×1.0127 (ECAL_EM 1.018→1.031), HAD ×1.3847 (ECAL_HAD 1.115→1.544,
HCAL_HAD 1.006→1.392). Realistic-digi factors ~identical (saturation negligible ≥GeV).
HEADLINE before→after median response:
- Neutral hadrons (n,K_L) E≥20 GeV: **0.777→1.005** (η0.5), **0.821→1.070** (η1.0). HAD CALIBRATED.
- γ ~1.0 (EM was right); μ 1.00 res 1%; e/π ~1.0, charged-eff 0.76-0.97 (η≤1.0).
LIMITATIONS found/scoped:
- Low-E neutral hadrons (≤1-2 GeV) under-respond / not reconstructed (HCAL threshold + non-comp).
- **η=2.0 endcap: charged-tracking efficiency ≈0** (e/μ/π not track-matched; reco as neutral) —
  ACTS seeding/CKF or track-state acceptance at high η. Charged PF validated barrel+transition η≤1.0.
- μ at η=2.0 response collapses (0.05-0.45) — not reconstructed as charged; endcap muon gap.
- γ@100 GeV η0.5 after-resp 1.388 (high-E EM outlier / low stats) — investigate.
- SC: CLD weights retained (on); full ODD CALICE refit scoped. Photon-ID retrain scoped (needs 30k).
  Pandora resolution TERMS (Stage 4): resolution characterized (σ/E plots); explicit term-tuning is a
  low-impact reclustering refinement — documented, scoped.
Stack note: validation at 200 ev (calibration) / 100 ev (validation passes), η∈{0.5,1.0,2.0} (η2.5
  endcap sims still building on node2). Defensible first full calibration; high-stats + η2.5 = follow-up.

## ENDCAP FIX (2026-05-30) — digi config audit + diagnosis
User asked: what ACTS digi am I using? did I look at the ttbar production digi/reco yaml?
- WAS using stock `odd-digi-smearing-config.json` (Gaussian smearing, fixed 15µm) + maxSeeds=5 + GridTriplet.
- Production ttbar (`colliderml_dev/configs_production/hard_scatter/ttbar/digitization_config.yaml`) uses
  `odd-full-geo-digi-config.json` (GEOMETRIC digi: real cell segmentation, threshold 0.01, charge
  smearing, per-cell covariances) + num_seeds_per_spm=40 + SeedingAlgorithm.Default.
- A/B on cached mu- E50 η2.0 (re-ran ACTS on sim.root): forward eff stock=1.00 prod=0.99 (geometric digi
  WORKS on our ODD, keeps efficiency). σ(p)/p: stock~4.7, prod~4.0 — **production digi does NOT fix the
  inflated covariance (#25)**; that's a separate seeding-prior/converter issue (priors identical).
- ADOPTED production geometric digi as default in acts_tracking.py (self-contained copy
  testbed/configs/odd-full-geo-digi-config.json; overridable via K4ODD_ACTS_DIGI_CONFIG) + aligned
  seeding (40 seeds, Default). Calibration/validation should be regenerated on this digi for fidelity.
- KEY: seeding config byte-identical to canonical; ACTS forward eff ~1.0 with BOTH digis → the η=2.0
  charged-PF gap is PANDORA-side (DDTrackCreator forward-track ingestion), NOT tracking. Pandora fix next.

## ENDCAP CHARGED-PF BUG FOUND + FIXED (2026-05-30)
DECISIVE DIAGNOSIS (not tracking — Pandora):
- ACTS reconstructs η=2.0 muons at 100% (200/200). seeding config byte-identical to canonical. Tracking fine.
- Pandora DEBUG trace (forward vs barrel μ): forward track's AtCalo synth is CORRECT — projects to ECAL
  ENDCAP z=3200 (=m_eCalEndCapInnerZ), r=882. Barrel → r=1250 (=eCalBarrelInnerR). Both projections good.
- ROOT CAUSE: our Phase-B ACTS-track fallback in `DDTrackCreatorCLIC::TrackReachesECAL` (empty trackerHits
  branch) was **barrel-only**: `reachesCalorimeter = (radiusAtCalo >= eCalBarrelInnerR)`. Forward tracks
  enter on the endcap face → radiusAtCalo(882) < eCalBarrelInnerR(1250) → reaches=FALSE → DefineTrackPfoUsage
  skipped → canFormPfo never set → NO charged PFO at |η|>~1.5. (Barrel r=1250≥1250 passes, so η≤1 worked.)
- FIX (1 line): also accept endcap-reaching tracks:
  `reaches = (radiusAtCalo >= eCalBarrelInnerR) || (|zAtCalo| >= eCalEndCapInnerZ)`.
- Diagnostic aids added (gated K4ODD_DEBUG_CALO): [DBG pfo-usage]/[DBG pfo-final] in DefineTrackPfoUsage;
  ODDreconstruction.py Pandora OutputLevel now env-driven (K4ODD_PANDORA_DEBUG).
- BUILD: in-place rebuild on CFS fails (Gaudi confdb2 sqlite dbm "disk I/O error" on Lustre). New
  future-proof `testbed/scripts/rebuild_pandora.sh` builds in node-local /tmp, installs to CFS.
- DIGI: adopted production geometric digi (odd-full-geo) as acts_tracking.py default; A/B showed it keeps
  forward eff (0.99) but does NOT fix #25 covariance (~4 both). Calibration sims should be regenerated on it.

### ENDCAP FIX VALIDATED (muon, 2026-05-30)
After rebuild (node-local) with the 1-line TrackReachesECAL endcap fix:
| μ | charged_eff before→after | resp_med before→after |
|---|---|---|
| η=2.0 | 0.00 → **1.00** | 0.10 → **0.999** |
| η=2.5 | 0.00 → **0.96** | (collapsed) → **0.997** |
| η=0.5 | 1.00 → 1.00 (no regression) | 1.003 |
Muons at the endcap now form charged PFOs (PID 13). Confirming e-/π- next, then full endcap re-validation.

### DOUBLE-FREE ROOT-CAUSED + FIXED (ABI, 2026-05-30)
After the endcap rebuild, ALL recos (barrel too) exited 134 `double free or corruption` at FINALIZATION
(output still valid — event processing correct). Root cause: ABI mismatch. build-ci/CMakeCache is a MIXED
stack (LCContent releases/2026-04-08 + PandoraSDK releases/2026-02-01); my rebuild_pandora.sh pinned
`-r 2026-02-01` → linked LCContent 2026-02-01, but the RUNTIME loads LCContent 2026-04-08 (default
$KEY4HEP_SETUP). Mismatched LCContent ABI → finalization double-free. FIX: rebuild_pandora.sh now sources
the DEFAULT stack (no -r), matching the runtime. Verified: reco exit=0, double-free=0, μ η2.0 charged_eff=1.00.
Memory updated (feedback_gaudi_confdb2_lustre_build). Clean revalidation (v3) running.

---

## 2026-05-30 — Two-week talk roadmap: de-risk spikes (Phase 0) + 3 fixes

Goal reframed for a physics talk in 2 weeks: (1) PFOs+clusters on a REAL event, (2) calo digitised
realistically, (3) calibrated end-to-end. Approved roadmap: peppy-rolling-hartmanis.md.

**Decisive finding:** the heavy sims already exist under
`/global/cfs/cdirs/m4958/data/ColliderML/simulation/` — hard_scatter/ttbar/v1, full_pileup/ttbar/v1,
**pileup-200/gg2ttbar/v1 (μ=200)**. Each `runs/<n>/edm4hep.root` has calo SimHits + MCParticles +
tracker Readout collections — exactly what `acts_tracking.py` consumes. So the demo = re-track (cheap)
+ Pandora reco (cheap); NO generation / μ=200 ddsim needed. Retires the biggest risk.

**Spike A (realistic-digi sanity, cached buckets):**
- HCAL realistic digi (after the =2→=1 fix in run_all_stages.sh) ENGAGES: neutron_E50 response
  0.9742 → 0.9490 (−2.6%, SiPM saturation). The bug mattered (old "real" constants ≈ ideal because
  HCAL=2 was a silent no-op).
- ECAL realistic digi (=1) errored: `Check setting of ECAL_apply_realistic_digi` — DDCaloDigi layer
  guard (`m_layerTypes[layer+1] != SIECAL`). Root cause: `ECAL_default_layerConfig="000000000000000"`
  (15 chars → 30 entries) but ODD ECAL = **48 layers**; layers ≥29 fell to (-99,-99). FIX:
  `ECAL_default_layerConfig = "0"*48` (96 entries). After fix: 0 errors, gamma 1.0060→1.0063 (Si digi
  near-lossless — correct physics). Both calo subsystems now realistically digitised.

**Spike B (production ttbar → PF):**
- Failed first at `acts_tracking.py:137 SeedingAlgorithm.Default` AttributeError. Our acts_main ACTS
  renamed the enum: `Default` → **`GridTriplet`** (members: GridTriplet, OrthogonalTriplet, Gbts,
  Hashing, HoughTransform, …). This is task #38's latent bug — the script was edited to production
  seeding but never run. FIX: `SeedingAlgorithm.GridTriplet`. Unblocks Phase 1 re-tracking too.
- After fix: 1 ttbar event → 15–38 ActsTracks/event (sensible), Pandora reco rc=0, **106 PFOs + 106
  clusters**, PID mix {±211, ±13, ±11, 22, 2112}, no crash. Energy closure (the 0.043 vs all-η truth
  was 13 TeV of beam remnants at |η|>4): in-acceptance ΣE_PFO/visE = **0.67 (|η|<4), 0.83 (|η|<3.5)** —
  healthy ~70–80%, to be refined by jet-level calibration. Calo SimHit raw 9.3 GeV → sampling-corrected
  ~590 GeV consistent. **The production-file → PF path works with zero new wiring.**

Fixes landed: (1) run_all_stages.sh `K4ODD_HCAL_REALISTIC_DIGI` 2→1; (2) acts_tracking.py
`SeedingAlgorithm.Default`→`GridTriplet`; (3) ODDreconstruction.py `ECAL_default_layerConfig`="0"*48.

## 2026-05-30 — Cluster-position investigation (user: "clusters wildly misplaced")

Verdict: NOT a viz bug — a real Pandora clustering pathology, exposed by the first multi-particle event.
- Single-photon clusters are CORRECT: stored position == energy-weighted CoG of ECAL hits (r=1312 vs
  1313), 0 warnings. So the CoG write (DDPfoCreator::setClusterPositionAndError, ClusterShapes) is fine.
- ttbar event: recomputed every cluster's CoG from its podio-linked hits — stored == CoG for all 106
  (the position write faithfully reports the centroid). BUT 13/106 clusters contain calo hits spanning
  BOTH endcaps: clu3 hit-z ∈ [-5178,+4004], energy split +z/-z = 62/38%; clu14 (E=20.8) 87/13; clu21
  44/56. Their centroids land near origin (r~80-440, |z|<900) — the "misplaced" look. A real shower
  can't deposit in both endcaps → Pandora is merging spatially-opposite endcap hits.
- Hit-level inputs are correctly signed: DDCaloHitCreator getCommonCaloHitProperties sets
  m_positionVector=(x,y,z) signed, m_expectedDirection=unit(pos); getEndCapCaloHitProperties sets
  m_cellNormalVector=±(0,0,1) by sign(z). DDGeometryCreator defines one symmetric endcap SubDetector
  (m_innerZCoordinate>0, standard Pandora). So the merge is in Pandora's clustering/pseudolayer layer,
  not the hit positions. Single-particle validation can't see it (1 particle → 1 endcap). Task #52.
- Tooling: testbed/scripts/check_cluster_cog.py (note: my first pass had a bug that falsely reported
  0 mismatch — corrected by direct per-hit dump).

Phase 1 (geometric-digi re-tracking) DONE: 209/216 (7 corrupt high-E sims; calib points E10/E50 OK).

### #52 isolation: cone-clustering, not associations
Ran the ttbar event with the primary ClusterAssociation DISABLED (PandoraSettingsCLD_noassoc.xml).
Both-endcap clusters: 13 (full) -> 11 (no assoc), total clusters 106 -> 132. So the merge happens in
ConeClustering (ClusterFormation) itself, not TopologicalAssociation. Hit positions/directions/normals
are correctly signed; pseudolayer plugin is the same generic LCContent::RegisterBasicPlugins used by the
validated DDMarlinPandora (neither registers a DD pseudolayer plugin). => root cause is the ODD endcap
GEOMETRY fed to Pandora via DDGeometryCreator (endcap innerZ/symmetry/layer extents), making the cone
clustering bridge +z/-z. Deep geometry-debug + rebuild task; mitigation for the talk demo = pick a
barrel-central event or show it as a known forward-region limitation.

## 2026-05-30 — "Charged 2x double-counting" was a validation harness bug, NOT physics

Phase 4 (val_real) showed e-/pi- median response ~2.0 (charged double-counting: track PFO + a separate
neutral PFO for the same shower), neutrals ~1.0. Chased it with isolation reco's on e-_E50_eta0.5:
- geom tracks + IDEAL digi + ideal const -> 0.997 (1 PFO) ✓
- geom tracks + ECAL=1/HCAL=1 + IDEAL const -> 0.997 ✓
- geom tracks + ECAL=1/HCAL=1 + REAL const (exact real scales) MANUAL -> 0.997 ✓
- same bucket from the SWEEP -> 2.006 ✗
Diff in the logs: sweep used **PandoraSettingsMinimal.xml**, manual used PandoraSettingsCLD.xml. Root
cause: `k4ODD/setup.sh:116` defaults `K4ODD_PANDORA_SETTINGS` to PandoraSettingsMinimal.xml (no
charged-PF chain); validate_fast.sh sourced setup.sh, so _val_inner's `${K4ODD_PANDORA_SETTINGS:-CLD}`
saw it already set to Minimal and kept it. reco_iter.sh avoided this by expanding the `:-CLD` default
PARENT-side (before setup.sh). FIX: validate_fast.sh now force-exports K4ODD_PANDORA_SETTINGS=CLD after
sourcing setup.sh. The Phase-2 realistic-digi CONSTANTS are correct; the val_real sweep was invalid and
is being re-run with CLD. (The forward-gamma 1.51 in that sweep is likely also a Minimal-settings
artifact — re-validate before trusting any residual.)

## 2026-05-30 — Corrected realistic-digi validation (CLD settings) — TRUE residual map

val_real (209 rows, CLD settings, realistic digi, calib_constants_real.env). Charged PF is excellent:
e-/mu-/pi- median response ~1.00 at all eta for E>=1 (the "2x" was the Minimal-settings harness bug).
Neutrals ~1.0 central. Coverage: 68% within +-5% for E>1 GeV; charged ~100%.

REAL residuals (not artifacts):
- Forward + high-E GAMMA over-response (leading-PFO energy inflation, single cluster): gamma fine
  (~1.0) for E<=20 at all eta, but at E>=50 the forward region inflates — eta2.0: 1.21/1.53/1.57 at
  E50/100/200; eta2.5 similar; eta0.5 hits 1.43 at E100. This is PRE-EXISTING (val_ideal had 1.19/1.31
  at E50) -> a forward/high-E ECAL EM non-linearity, NOT a realistic-digi effect, NOT #52. (R1)
- Low-E floor: charged fail <1 GeV (track too soft), neutron fails <5 GeV, kaon0L low at <1 GeV.
  Genuine reconstruction limits (gamma still works down to 0.5 GeV: 0.95).
- Minor: kaon0L slightly high (1.02-1.11), neutron slightly low (0.97).

Validation infra: validate_fast.sh (single-shifter, xargs -P, env+constants once) + _val_inner.sh.

## 2026-05-30 — Phase 5 demo + Phase 6 deck COMPLETE

ttbar PF demo (30 events, final realistic-digi constants + CLD settings): jet energy response median
1.027, IQR/med 0.21, reco/truth jet multiplicity 8.3/8.3, event energy closure 1.01. Charged
double-counting absent (confirming it was the Minimal-settings harness bug). Tools: jet_analysis.py
(anti-kt R=0.4 via fastjet), event_display.py (r-z + x-y, digi calo hits + PF clusters). Central event
18 (84% barrel) used for the cleanest display.

Deck (testbed/deck/calibration.pdf, 1.58 MiB) rebuilt with: realistic-digi story + the 3 bug fixes,
corrected validation_real plots, the ttbar demo (event display + jet validation), updated limitations
(forward high-E gamma R1, forward both-endcap clustering #52, low-E floor, pileup-next).

THREE TALK CLAIMS now evidenced: (1) PFOs+clusters on a real ttbar event w/ jet validation;
(2) calo realistically digitised (ECAL Si + HCAL SiPM); (3) calibrated end-to-end (charged ~1.0 all eta,
neutral ~1.0 central). Remaining deep residuals: R1 (forward high-E gamma), #52 (forward clustering),
mu=200 pileup (sims exist, same path).

## 2026-05-30 — μ=200 "Pandora too slow" was an O(N²) truth-link bug in OUR code

Initial μ=200 reco (full_pileup/ttbar/v1) ran >1h40m on ONE event, killed by the SLURM time limit with
no PFOs. I wrongly concluded "Pandora intractable at μ=200." User pushed: profile before blaming the
algorithm. Did so:
- Stack-sampled the live process: gdb/eu-stack `bt` gave `?? ()` (no loaded symtab), so resolved the
  hot address via /proc/<pid>/maps -> library + offset -> nm/addr2line on the (not-stripped) .so on CFS.
  NOTE: /proc/maps shows the shifter host path `/var/udiMount/...`; strip that prefix to read the lib.
- Hot frame: `DDMCParticleCreator::CreateCaloHitToMCParticleRelationships` calling
  `podio::LinkT::getFrom()` / `CalorimeterHit::getObjectID()` in a tight loop — same region every sample.
- Source: nested `for(calo hit N) for(link M) if(ids != ) continue;` — a LINEAR SCAN of the whole
  CaloHit<->SimCaloHit link collection for EVERY calo hit. N,M ~ 1e5 at μ=200 -> ~1e10 ops -> hours.
  (Hard-scatter ttbar: ~1e3 hits -> 1e7 ops -> seconds. That's why single-particle/hard-scatter were fine.)
- It is MC-TRUTH bookkeeping; Pandora itself never ran.

FIX (DDMCParticleCreator.cc): build an unordered_set of selected hit keys once, iterate each link
collection ONCE with O(1) membership -> O(N+M). ~5e4x fewer ops for the stage. Semantics preserved
(digi CaloHit<->SimCaloHit link is 1:1/hit). Sibling CreateTrackToMCParticleRelationships has the same
pattern but N=1299 tracks (~1e6 ops, not a bottleneck) — left as a follow-up. Rebuilt k4GaudiPandora
node-local (rebuild_pandora.sh). LESSON: profile (stack-sample + resolve symbols) before declaring an
algorithm intractable.

## 2026-05-30 — μ=200 PF: COMPLETE timing attribution + first result

Comprehensive profiling (stack-sample live process w/ eu-stack/gdb -> resolve via /proc/maps -> nm on
the not-stripped .so on CFS, stripping the /var/udiMount shifter prefix) of full_pileup/ttbar/v1 mu=200:
1. ORIGINAL >1h40m-killed run: stuck in DDMCParticleCreator::CreateCaloHitToMCParticleRelationships
   (OUR O(N^2) truth-link bug). FIXED (unordered_set, O(N+M)) + rebuilt. ~1h40m -> seconds.
2. AFTER fix: bottleneck moved to Pandora lc_content::ClusterContact::HitDistanceComparison (12/12
   samples) — pairwise cluster-contact hit-distance, used by topological association + FragmentRemoval +
   the 12-pass reclustering. Disabling the primary association block alone did NOT help (still in
   ClusterContact via FragmentRemoval/reclustering).
RESULT: mu=200 event RECONSTRUCTS — 6502 PFOs, SumE=24.8 TeV, PID {3168 gamma, 2036 n, 856 pi, 442 e}.
Wall-time 1h41m (reduced-assoc config). Event display: testbed/results/demo/ttbar_mu200_event0.png.
Two ~1h40m costs were stacked: (1) our truth-link O(N^2) [fixed], (2) Pandora ClusterContact O(N_clu^2)
[genuine]. Residual optimization levers (not yet done): disable/limit the 12-pass reclustering
(SplitTrackAssociations, config), tighten ClusterContact distance cuts, or spatial-index cluster pairs
(upstream Pandora SDK). mu=200 dataset compatibility: full_pileup/ttbar/v1 (stave:15:1) works;
pileup-200/gg2ttbar/v1 (no stave) does NOT (older ODD geometry).

### μ=200 timing — DEFINITIVE call structure (full-stack resolution)
Full resolved backtrace of the slow phase:
  #3 lc_content::BackscatteredTracks2Algorithm::Run
  #2 lc_content::ClusterHelper::GetDistanceToClosestCentroid
  #0/1 pandora::Cluster::GetCentroid
Earlier statistical samples: lc_content::ClusterContact::HitDistanceComparison (FragmentRemoval).
=> The cost is the TOPOLOGICAL ASSOCIATION chain (~13 algos: BackscatteredTracks, ShowerMipMerging,
ProximityBasedMerging, FragmentRemoval, ...), each scanning cluster PAIRS (O(N_clusters^2), NO spatial
pruning) and computing inter-cluster geometry (GetDistanceToClosestCentroid->GetCentroid, closest-hit),
run ITERATIVELY to convergence AND repeated across the 12-pass reclustering (SplitTrackAssociations).
Product: O(N_clu^2) x per-pair-geometry x ~13 algos x iterations x 12 recluster passes -> ~1.5h at
mu=200 (~6500 clusters). NOT "6000^2 = seconds": the multipliers + zero spatial indexing are the hours.
Pandora HAS KDTreeLinkerAlgo (used for track-cluster assoc) but the topological-association algos don't
use it for cluster-pair pruning. FIX = spatial-index the cluster pairs (KD-tree on centroids), O(N logN)
— upstream LCContent change. (The GNN4ITk contrast is exact: same NN problem, brute-force all-pairs.)

### CORRECTION (2026-05-30): association is NOT the dominant cost — ConeClustering is
Timed the "fast" config (NO topological association, NO reclustering): 15:47:48 -> 17:35:51 = 1h48m,
i.e. LONGER than the full chain (1h41m). So removing the association did NOT help -> the association is
NOT the bottleneck. The dominant cost is the PRIMARY ConeClusteringAlgorithm (present in both), ~1h40m
at mu=200. My earlier "association O(N^2)" conclusion was from sparse stack samples, not wall-time
attribution — wrong. Lesson (user): TIME EVERY STEP comprehensively (hard-scatter first) before fixing.
ConeClustering profiling showed FindHitsInSameLayer / GetDistanceToHitInSameLayer + an iterative
while(!available_hits)/while(clustersModified) re-scan; it DOES use KD-trees but the re-scan is the cost.
NEXT: per-algorithm timing on hard-scatter (perf or instrument PandoraSDK dispatch), then fix the real one.

### DEFINITIVE per-algorithm self-time profiler (2026-05-30) — instrumented PandoraSDK
Built a per-algorithm self-time profiler into PandoraSDK v03-04-01 (instrument
PandoraContentApiImpl::RunAlgorithm: push/pop a child-time stack so each algo's SELF time excludes
its sub-algorithms; dump via DumpPandoraAlgorithmTiming() in Pandora::ProcessEvent under
PANDORA_ALG_TIMING). SONAME forced to .03.04 + LD_PRELOAD (RPATH beats LD_LIBRARY_PATH).

HARD-SCATTER ttbar, 60 events, self-time totals (the real ranking — supersedes both earlier guesses):
  MainFragmentRemoval        25.1 s   <-- #1
  ConeClustering             22.6 s
  NeutralFragmentRemoval     18.9 s   <-- #3
  SoftClusterMerging          9.4 s
  CaloHitPreparation          8.0 s
  IsolatedHitMerging          5.0 s
  BackscatteredTracks(x2)     4.9 s
  TrackClusterAssociation     4.2 s
  ProximityBasedMerging       2.3 s
=> The FRAGMENT-REMOVAL family (Main+Neutral = 44 s) is the single largest cost, ahead of the primary
ConeClustering. (My two prior conclusions — "association" then "ConeClustering" — were both wrong;
only a self-time profiler attributes correctly. User's instruction to time every step first: vindicated.)

ROOT CAUSE (Main/Neutral FragmentRemoval): GetChargedClusterContactMap / GetNeutralClusterContactMap run
a brute-force O(N_cluster^2) double loop, constructing a (Charged/Neutral)ClusterContact for EVERY
daughter/parent pair. That constructor calls ClusterContact::HitDistanceComparison — an O(hits_d x hits_p)
all-hit-pairs loop with NO spatial early-out. At mu=200 (~6500 clusters) this is the dominant term.

THE FIX (provably IDENTICAL, not approximate): PassesClusterContactCuts' FIRST gate is
  if (GetDistanceToClosestHit() > m_contactCutMaxDistance) return false;   // 750 mm Main / 500 mm Neutral
so a pair is only ever kept if its closest hit-pair is within that distance. Precompute each parent
candidate's bounding sphere (geometric hit centre + enclosing radius) ONCE; skip any daughter/parent pair
whose sphere separation (centreSep - rD - rP) exceeds m_contactCutMaxDistance — the true closest hit can
only be farther, so the original would have rejected it at that gate. No KD-tree needed; the per-event
precompute is O(total hits), the pruned search scales with local density. Result is byte-identical to
stock (skips only pairs guaranteed to fail). Implemented in MainFragmentRemovalAlgorithm.cc (anonymous-
namespace GetClusterBoundingSphere + parentBoundingSpheres precompute + pre-check); same pattern for
NeutralFragmentRemovalAlgorithm. Validation = my-built-stock-LCContent vs my-built-opt-LCContent (same
toolchain, LD_PRELOAD'd over cvmfs; PandoraSDK must be preloaded first as LCContent's Pandora symbols are
undefined-at-load), compare GaudiPandoraPFOs+Clusters (testbed/scripts/validate_fragremoval.sh).

### μ=200 REAL bottleneck found (2026-05-31) — TOPOLOGICAL ASSOCIATION family, not FragmentRemoval
Manual stack-scan (raw $rsp walk + addr2line on libLCContent return-addrs; the unwinder is broken at
-O2 and PC-symbolization mislabels the hot code as std::endl — a COMDAT-folded weak symbol) on a live
clean μ=200 reco gives the TRUE call chain:
  TopologicalAssociationParentAlgorithm::Run
    -> {ProximityBasedMerging, ShowerMipMerging3, BackscatteredTracks, ...}::Run
       -> ClusterHelper::GetDistanceToClosestCentroid / GetGenericDistanceBetweenClusters
          -> CartesianVector::GetDistanceSquared
6 scans: ProximityBasedMerging x3, ShowerMipMerging3 x2, BackscatteredTracks x1, TopoAssocParent x1.
=> The TOPOLOGICAL ASSOCIATION chain (~17 algos in src/LCTopologicalAssociation/) is the μ=200 cost:
each loops over cluster PAIRS (O(N_clu^2)) computing an inter-cluster distance with NO spatial pruning,
run iteratively to convergence by TopologicalAssociationParentAlgorithm. Cheap at hard-scatter (~225
clu, 4.9s) but dominant at μ=200 (~6500 clu -> ~20 min/event). This is the SAME O(N^2)-cluster-pair
class as FragmentRemoval and takes the SAME bounding-sphere prune (skip pairs whose sphere separation
exceeds the algo's max distance cut; identical output). Fix the top few by self-time (await -O2 ALGTIME
table), shared GetClusterBoundingSphere helper. NOTE: the earlier "association is the bottleneck"
hypothesis (pre-FragmentRemoval) was RIGHT for μ=200; the hard-scatter self-time "correction" only held
at low N. Both FragmentRemoval (done) and the association family are real O(N^2) cluster-pair bugs.

### Topological-association bounding-sphere fix — IMPLEMENTED + byte-identical (2026-05-31)
Added shared ClusterHelper::GetClusterBoundingSphere (geometric hit centre + enclosing radius). Applied the
bounding-sphere prune to the hot O(N_clu^2) cluster-pair association algos (precompute spheres once; skip a
pair when (centreSep - rA - rB) > D before the expensive inter-cluster distance call; MERGE-UPDATE: recompute
the parent sphere after MergeAndDeleteClusters since merges grow clusters mid-loop):
  - BackscatteredTracksAlgorithm   D = m_maxCentroidDistance (100mm)  [closest-centroid gate]
  - ShowerMipMerging3Algorithm     D = m_maxClusterApproach  (250mm)  [closest-hit gate]
  - ProximityBasedMergingAlgorithm D = sqrt(m_maxGenericDistance^2 + m_maxParallelDistance^2) (~1001mm)
    [perp+parallel reach; pre-check placed AFTER the energy-consistency early-return at line 130 so control
     flow is byte-for-byte unchanged]
Each bound is provably safe (the gate distance >= sphere separation, so only pairs guaranteed to fail are
skipped). VALIDATION hard-scatter 30ev, my-built-stock vs my-built-opt LCContent: PFO 6786/6786, CLUSTER
6771/6771, max|Δ|=0.0 IDENTICAL (BackscatteredTracks alone first, then all 3 together). Same validated for
FragmentRemoval earlier. Opt also already faster on cluster-sparse hard-scatter (124s vs 135s). NEXT: measure
μ=200 wall (mu200_assocfix_ab) — the real proof at ~6500 clusters; if still slow, stack-scan for the next
association algo (ShowerMipMerging1/2/4, BackscatteredTracks2, BrokenTracks, LoopingTracks, ConeBasedMerging)
and patch same pattern. Note: GetClusterBoundingSphere went into ClusterHelper (shared); FragmentRemoval keeps
its own file-local copy from the earlier fix.

### μ=200 tractability (2026-05-31): event-wise parallelism + ConeClustering rewrite
PARALLELISM (user ask: how parallelizable, naively event-wise, on exclusive CPU node): tested N=64
concurrent independent recos on a Perlmutter CPU node (256 threads, 503GB). Per-proc walls 85-93s
(mean 87s) vs ~85s single-process = ~2% slowdown at 64-way concurrency -> NEAR-LINEAR. Memory is the
limit (~7GB/reco -> ~64-70 concurrent on 503GB), not threads. => μ=200 demo is tractable: ~64 events in
~24min wall (with the bounding-sphere-fixed opt lib). testbed/scripts/parallel_throughput_test.sh.

CONECLUSTERING (user: drop byte-identical, require metrics within a %): the cost was the
while(clustersModified) FULL re-scan of all available hits every pass (O(passes x N_avail)). Rewrote
FindHitsInSameLayer as a WORKLIST: each hit (re)evaluated only when first queued or when a NEIGHBOUR
joins a cluster (propagated via cached hitsToHitsLocal). Per-hit association decision + one-seed-at-a-
time-with-convergence structure UNCHANGED -> metrics-equivalent, scales with local density not N_hits^2.
Compiles. Validating metrics (compare_metrics.py, tolerance %) stock-vs-opt hard-scatter, then μ=200
speedup. Opt lib now = bounding-sphere(5 algos, byte-identical) + ConeClustering worklist(metrics-equiv).

---

## 2026-06-01 — Calibrated μ=200 physics + throughput scaling, then R1 ROOT-CAUSED & FIXED + full consistency revalidation

After the μ=200 reco was made tractable (10.6 min/event, byte-identical; see OPTIMIZATION_LOG.md), the
talk was reframed around **three tiers of maturity**: (1) single-particle calibration, (2) hard-scatter
jets, (3) μ=200 pileup. Built a re-runnable plot-pool notebook `testbed/notebooks/tier_performance.ipynb`
(+ shared `perf_lib.py`, pileup-aware `jet_analysis.py`) that regenerates every figure from the latest
reco outputs. Ran calibrated μ=200 (64 events) + a concurrency scaling study (22/44/80/156 events/node-hour
at P=8/16/32/64, near-linear, memory-bandwidth bound on one EPYC-7763 128-core node).

### R1 (high-E EM over-response) — the long-open residual, now solved
The Stage-7 validation had flagged a forward + high-E **γ/e over-response** (γ E100 1.43, E200/η2 1.57)
as a "pre-existing ECAL EM non-linearity" (open residual). Diagnosed it properly by dissecting the cached
`reco_valreal` outputs:
- **Not fragmentation** (the leading PFO is itself over-scaled), **not the digitisation** (present in
  ideal-digi too, only ~3% from realistic digi), **not software compensation** (SC weights identical
  between linear and non-linear configs). Uncalibrated Pandora is **linear** (lead resp 1.02 at E100) —
  **the calibration introduced it.**
- **Root cause:** the only large E-dependent calibration term is `ECalToHadGeVCalibrationBarrel`. The
  Stage-2 calibration had set it to **1.587** (its 2-point fit loaded the whole hadronic correction onto
  the ECAL→Had constant — exactly the "hadrons deposit a large fraction in ODD's deep ECAL, reconstructed
  via the ECAL→Had calibration" finding from Stage 2 above). But this same constant **hadronic-scales the
  EM-shower energy that leaks into late-ECAL/HCAL layers** — negligible at low E, large at high E (and
  forward, where showers are more collimated) → the over-response.

### Fix = ECAL/HCAL hadronic rebalance (measured, not guessed)
A HAD-scale scan (γ E100 + K⁰_L E50 at ECAL→Had ∈ {1.10,1.30,1.587}) confirmed a genuine EM/HAD tension:
γ wants ECAL→Had≈1.1, neutral hadrons want ≈1.59. Resolved it by **rebalancing onto the HCAL** (photons
are ECAL-dominated and HCAL-insensitive; neutral hadrons are HCAL-dominated):
- **`ECalToHadGeVCalibration{Barrel,EndCap}` 1.587 → 1.10**, **`HCalToHadGeVCalibration` 1.43 → 1.90**.
- A **cliff scan** set HCAL: 2.05 over-boosts low-E muon MIP deposits (spurious neutral; mu E2 1.0→3.14);
  the central-muon cliff is between 1.95 and 2.00, so **1.90** is the safe optimum (mu E2 1.01, hadrons
  K⁰_L 0.99 / neutron 0.96).
- Applied to `testbed/results/calib_constants_real.env` (old values kept in comments). **FINAL realistic-
  digi constants: EM 1.031, ECAL→Had 1.10, HCAL→Had 1.90.** (The ideal-digi env still carries the old
  ECAL→Had 1.544 — same latent issue, not re-derived; talk uses realistic digi.)

### Full consistency revalidation (everything regenerated with 1.10/1.90)
Re-ran, on fresh nodes, the **complete pipeline**: 216-bucket single-particle grid (`validate_fast.sh` →
new `val_real.jsonl`; pre-R1 backed up to `val_real_preR1.jsonl` + `acceptance_table_preR1.txt`), Tier-2
hard-scatter (`reco_r1.root`), 64-event μ=200 (`reco_cal_*`), per-type, the notebook (all `talk_plots`),
and the deck.

| metric | before (1.587/1.43) | after (1.10/1.90) |
|---|---|---|
| γ E100 η0.5 / E200 η2.0 | 1.43 / 1.57 | **1.03 / 1.09** |
| e⁻ E200 η2.0 | 1.57 | **1.08** |
| central μ E2 / E10 | 1.00 / 1.00 | 1.01 / 1.00 |
| K⁰_L / neutron E50 | ~1.0 | 0.99 / 0.96 |
| worst \|med−1\| (E≥5) | 0.567 (γ E200) | **0.433** (neutron E5, intrinsic) |
| Tier-2 hard-scatter jet E resp / IQR-med | 1.027 / 0.21 | **0.977 / 0.16** (tighter) |
| Tier-3 μ=200 energy flow ΣE_PFO/vis | 0.92 | **0.88** |
| Tier-3 μ=200 pileup-subtracted hard-jet pT | 0.97 | **0.84** |

**Honest tradeoff:** the fix corrects the high-E EM bug AND tightens jet resolution (21→16%), but the
μ=200 energy scale drops (0.92→0.88) because the old calibration was *over-boosting* hadrons (the 0.92 was
partly an artifact); hadrons now sit at their true ~0.96. **Two residuals, both pre-existing, neither caused
by R1:** (1) forward low-E muon *energy* over-responds (spurious-neutral MIP — muon momentum from the track
is unaffected; Pandora muon-ID limitation); (2) low-E (<5 GeV) neutral hadrons under-respond (intrinsic
HCAL-threshold/non-compensation). Both documented in the deck limitations + summary.

### Current state — three tiers all defensible (final calibration)
- **Tier 1 (single particles):** γ/e/μ excellent at all E and η (high-E EM now fixed), μ resolution 1%,
  neutral hadrons 0.96–0.99 for E≳20 GeV. Full 216-bucket grid revalidated.
- **Tier 2 (hard-scatter jets):** jet E response 0.977, IQR/med 16%, ΣE closure 0.96, multiplicity 8.3 vs 8.3.
- **Tier 3 (μ=200 pileup):** runs tractably (5.66×, byte-identical), energy flow 0.88, pileup-subtracted
  hard-jet pT 0.84.
