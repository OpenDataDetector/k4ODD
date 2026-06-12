# ODD calorimeter digitisation + particle-flow calibration guide

How the Open Data Detector calorimeter digitisation and PandoraPFA reconstruction were calibrated
end-to-end, what every knob does, the final constants, and the known residuals. The blow-by-blow
history (every iteration, dead end and measurement) is in `doc/CALIBRATION_JOURNAL.md`; speed
optimization in `doc/OPTIMIZATION_LOG.md`. **All particle-flow evaluation goes through
k4DetectorPerformance's PFONtuple** (`ci/make_truth_links.py` + `runPFONTuple_ODD.py` +
`ci/check_pfontuple.py`).

## The chain

```
ddsim (Geant4, ODDsimulation.py)
  └─ SimCalorimeterHits + tracker Readout SimTrackerHits + MCParticles
DDCaloDigi (in ODDreconstruction.py / ODDdigitisation.py)        [DIGI scale layer]
  └─ CalorimeterHits (MIP-calibrated GeV) + CaloHit<->Sim links
DDPandoraPFANewAlgorithm (k4GaudiPandora + PandoraSDK + LCContent)  [PANDORA scale layer]
  └─ GaudiPandoraPFOs / Clusters / StartVertices
```

Two independent scale layers: the **digi MIP scale** converts deposited energy to calibrated
cell GeV; the **Pandora EM/HAD scales** convert calibrated cells to particle energies, split by
shower hypothesis. They were calibrated in that order, on **realistic digitisation** (the
defaults shipped in `ODDreconstruction.py`).

## Stages (each validated before the next)

| stage | what was done | tools |
|---|---|---|
| 0 | Calibration-iteration infrastructure: env-knob interface (no file edits per iteration), per-bucket sim cache so digi/reco re-run without re-Geant4 | `ci/run_one_bucket.sh`, env knobs |
| 1 | Geant4 sim cache: 216 buckets = 6 particles (γ, e⁻, μ⁻, π±, n, K⁰_L) × 9 energies (1–200 GeV) × 4 η (0, 0.5, 1, 2) | SLURM array |
| 2 | Calo energy-scale calibration on ideal digi: 2-point solve, EM from γ@10 GeV, HAD from n/K⁰_L@50 GeV | `ci/calibrate_scale.py` |
| 3 | Software compensation: CLD/CALICE 9-weight set retained after an ODD refit attempt showed the full re-derivation needs per-hit cell-volume density + the PandoraAnalysis training framework (deferred, R3) | `K4ODD_SOFTCOMP_WEIGHTS` |
| 4 | Pandora resolution terms (EM/HAD stochastic+constant) set to measured single-particle resolutions | `K4ODD_{EM,HAD}_{STOCH,CONST}` |
| 5 | **Realistic digitisation enabled** (the gate): ECAL=1 silicon (Poisson + noise + dynamic range), HCAL=1 scintillator/SiPM saturation. Re-calibrated everything on it. Gotchas: HCAL switch has **no mode 2**; ECAL silicon path **asserts on non-Si geometry**; ECAL needed `layerConfig="0"*48` or silicon digi silently no-ops | stage-5 journal entries |
| 6 | PID: photon likelihood retrained (`PandoraLikelihoodData9EBin.xml`, 30k γ/n/K⁰_L events), electron/muon ID tuned | `--pandoraPhotonTraining` |
| 7 | Full validation suite over the 216-bucket grid (response, resolution, efficiency, PID purity per particle × E × η) | `ci/analyze_validation.py` |
| 7b | **R1 fix — high-E EM over-response**: γ/e response 1.4–1.6 at E≥100 GeV traced to `ECalToHadGeVCalibrationBarrel=1.587` hadronically over-scaling EM-shower leakage into late ECAL/HCAL. Rebalanced ECAL→Had 1.587→**1.10** + HCAL→Had 1.43→**1.90** (2.05 broke low-E muons: spurious-neutral MIP over-boost; the safe ceiling is below 1.95). Revalidated the full grid + jets + μ=200 | journal 2026-06-01 |
| 8 | Lock-in: constants promoted to in-code defaults, journals + this guide committed, PFONtuple CI regression added | this repo |

## Final constants (defaults in `ODDreconstruction.py`; also `options/calib_constants_real.env`)

| constant | value | layer |
|---|---|---|
| CalibrECAL (MIP) | 37.5227 ×2 layers, endcap corr 1.0324 | digi |
| CalibrHCAL barrel / endcap / other (MIP) | 45.996 / 46.925 / 57.459 | digi |
| ECAL/HCAL realistic digi | **1 / 1** (on) | digi |
| ECalToEM = HCalToEM | **1.0307411173318997** | Pandora |
| ECalToHad barrel = endcap | **1.10** | Pandora |
| HCalToHad | **1.90** | Pandora |
| EM stoch/const | 0.17 / 0.01 | Pandora |
| HAD stoch/const | 0.6 / 0.03 | Pandora |
| Software compensation | CLD/CALICE 9 weights | Pandora |

**Validated performance**: single particles — response ≈1.00±0.03 across the grid (γ E100 1.43→1.03
post-R1); hard-scatter ttbar jets — E response 0.977, IQR/median 16%, ΣE closure 0.96; μ=200 —
energy flow 0.88, pileup-subtracted hard-jet pT 0.97, 10.6 min/event with the optimized LCContent
(byte-identical, 5.66× vs stock).

## Knob reference (env overrides; defaults = calibrated values)

| knob | meaning |
|---|---|
| `K4ODD_CALIBR_ECAL`, `K4ODD_ECAL_ENDCAP_CORR` | ECAL MIP→GeV scale (list), endcap correction |
| `K4ODD_CALIBR_HCAL_{BARREL,ENDCAP,OTHER}`, `K4ODD_HCAL_ENDCAP_CORR` | HCAL MIP→GeV scales |
| `K4ODD_{ECAL,HCAL}_REALISTIC_DIGI` | 0=ideal; ECAL 1=silicon (2=scint asserts on ODD); HCAL 1=scint/SiPM (no 2) |
| `K4ODD_{ECAL,HCAL}_{DEADCELL_RATE,NOISE_MIPS,MISCAL}` | imperfection knobs (all 0.0 in the calibrated config) |
| `K4ODD_{ECAL,HCAL}_EM_SCALE` | Pandora EM-shower GeV calibration |
| `K4ODD_ECAL_HAD_SCALE_{BARREL,ENDCAP}`, `K4ODD_HCAL_HAD_SCALE` | Pandora hadronic GeV calibration (the R1 levers) |
| `K4ODD_{EM,HAD}_{STOCH,CONST}` | Pandora resolution terms |
| `K4ODD_SOFTCOMP_WEIGHTS` | 9 software-compensation weights |
| `K4ODD_PANDORA_SETTINGS` | settings XML (default Minimal; CLD for charged PF; see `doc/pandora_tuning_appendix.md`) |
| `K4ODD_TRACK_CREATOR` / `K4ODD_TRACK_COLLECTION` | `DDTrackCreatorEmpty`/`EmptyTracks` (calo-only) or `DDTrackCreatorCLIC`/`ActsTracks` |
| `K4ODD_MAX_TRACK_SIGMA_POVERP` | track-quality cut; 999 masks the inflated ACTS ω-covariance (#25) |
| `K4ODD_PANDORA_DEBUG`, `K4ODD_EVENTS`, `K4ODD_OUTPUT_DIR` | debug verbosity, event cap (digi), output redirection |

## Known residuals (the queue for the next calibration sprint)

1. **R2 — resolution-term refit** (#45): EM/HAD stochastic terms were set from ideal-digi fits;
   refit on realistic digi.
2. **R3 — software-compensation refit** (#46): CLD/CALICE weights are a defensible fallback; a
   real ODD re-derivation needs per-hit cell-volume density + the PandoraAnalysis training
   framework. Residual non-compensation slope at low E.
3. **R4 — e⁻/γ PID polish** (#47): photon likelihood was retrained, electron E/p cuts raised but
   not optimized.
4. **#52 — both-endcap cluster merging**: Pandora cone-clustering merges hits from ±z endcaps in
   forward events (~12% of forward clusters); needs a geometry-aware fix in LCContent.
5. **#25 — inflated ACTS→edm4hep ω covariance**: masked by `MaxTrackSigmaPOverP=999`; does not
   bias response but should be fixed at the converter and the mask removed.
6. **Low-E floors** (intrinsic): charged PF < 1 GeV, neutral hadrons < 5 GeV under-respond
   (HCAL threshold); forward low-E muon cluster energy over-responds (spurious-neutral MIP,
   momentum from track is correct).
