#!/usr/bin/env bash
# Run one ddsim + (optional ACTS tracking) + Pandora reco + analyse cycle for a
# single (particle, E, eta, N) bucket. Wraps each stage in shifter
# atlas-grid-almalinux9 + LCG_107 + key4hep release.
#
# Args (env):
#   PARTICLE        e.g. gamma, e-, mu-, pi-, pi+, neutron, kaon0L, pi0
#   ENERGY_GEV      e.g. 10.0
#   ETA             e.g. 0.5
#   NEVENTS         e.g. 100
#   SEED            random seed
#   BUCKET_DIR      absolute path to output dir for this bucket
#   ANALYSER        pfo_performance (default) | gamma_conversion | none
#   WITH_TRACKS     0 (default, calo-only DDTrackCreatorEmpty) | 1 (ACTS tracks +
#                   DDTrackCreatorCLIC). When 1, ddsim output is run through
#                   run_acts_tracking.sh to add an ActsTracks collection, and the
#                   Pandora reco is told to consume it.
#
# Writes into BUCKET_DIR:
#   sim.root, [sim_with_tracks.root], reco.root, pfo.root
#   ddsim.log, [acts.log], reco.log, analyse.log, bucket.json

set -euo pipefail

PARTICLE="${PARTICLE:?particle name required}"
ENERGY_GEV="${ENERGY_GEV:?energy_gev required}"
ETA="${ETA:?eta required}"
NEVENTS="${NEVENTS:?nevents required}"
SEED="${SEED:?seed required}"
BUCKET_DIR="${BUCKET_DIR:?bucket_dir required}"
ANALYSER="${ANALYSER:-pfo_performance}"
WITH_TRACKS="${WITH_TRACKS:-0}"

REPO_ROOT="${REPO_ROOT:?set REPO_ROOT to the working directory containing the k4ODD checkout}"

mkdir -p "$BUCKET_DIR"

cat > "$BUCKET_DIR/bucket.json" <<EOF
{
  "particle": "$PARTICLE",
  "energy_gev": $ENERGY_GEV,
  "eta": $ETA,
  "nevents": $NEVENTS,
  "seed": $SEED,
  "analyser": "$ANALYSER",
  "with_tracks": $WITH_TRACKS
}
EOF

# ---------- Stage 1: ddsim (always) ----------
shifter --image=registry.cern.ch/atlasadc/atlas-grid-almalinux9 --module=cvmfs bash -c "
set -eo pipefail
source /cvmfs/sft.cern.ch/lcg/views/setupViews.sh LCG_107 x86_64-el9-gcc13-opt >/dev/null
export KEY4HEP_SETUP=/cvmfs/sw.hsf.org/key4hep/setup.sh
cd '$REPO_ROOT'
source k4ODD/setup.sh
cd k4ODD
export K4ODD_OUTPUT_DIR='$BUCKET_DIR'
ddsim \
  --compactFile \"\$OpenDataDetector/install-ci/share/OpenDataDetector/xml/OpenDataDetector.xml\" \
  --steeringFile k4ODD/options/ODDsimulation.py \
  --enableGun --gun.distribution uniform \
  --gun.particle '$PARTICLE' --gun.energy '${ENERGY_GEV}*GeV' \
  --gun.etaMin '$ETA' --gun.etaMax '$ETA' \
  --numberOfEvents '$NEVENTS' \
  --outputFile '$BUCKET_DIR/sim.root' \
  --random.seed '$SEED' \
  > '$BUCKET_DIR/ddsim.log' 2>&1
"

# ---------- Stage 2: ACTS tracking (optional) ----------
RECO_INPUT="$BUCKET_DIR/sim.root"
TRACK_ENV=""
if [[ "$WITH_TRACKS" == "1" ]]; then
  SIM_FILE="$BUCKET_DIR/sim.root" \
    MERGED_FILE="$BUCKET_DIR/sim_with_tracks.root" \
    bash "$REPO_ROOT/testbed/scripts/run_acts_tracking.sh" \
    > "$BUCKET_DIR/acts.log" 2>&1
  RECO_INPUT="$BUCKET_DIR/sim_with_tracks.root"
  # Charged-particle-flow path: feed ACTS tracks (DDTrackCreatorCLIC) into the full
  # CLD charged-PF Pandora chain (TrackPreparation + reclustering + muon reco), and
  # relax MaxTrackSigmaPOverP since ACTS's EDM4hep covariance is inflated ~5e4x (the
  # omega VALUE is correct; only its error estimate is wrong, so the 0.15 default
  # would drop every good track). See ODDreconstruction.py + PandoraSettingsCLD.xml.
  TRACK_ENV="export K4ODD_TRACK_CREATOR=DDTrackCreatorCLIC; export K4ODD_TRACK_COLLECTION=ActsTracks; export K4ODD_PANDORA_SETTINGS='$REPO_ROOT/k4ODD/k4ODD/options/PandoraSettingsCLD.xml'; export K4ODD_MAX_TRACK_SIGMA_POVERP=999;"
fi

# SIM_ONLY=1 stops after sim (+tracks) — used to build the reusable sim cache so the
# calibration loop can iterate reco-only on cached sims without re-running Geant4.
if [[ "${SIM_ONLY:-0}" == "1" ]]; then
  echo "SIM_ONLY=1 — stopping after sim/tracks; reco skipped. RECO_INPUT=$RECO_INPUT"
  exit 0
fi

# ---------- Stage 3: Pandora reco + analyse ----------
shifter --image=registry.cern.ch/atlasadc/atlas-grid-almalinux9 --module=cvmfs bash -c "
set -eo pipefail
source /cvmfs/sft.cern.ch/lcg/views/setupViews.sh LCG_107 x86_64-el9-gcc13-opt >/dev/null
export KEY4HEP_SETUP=/cvmfs/sw.hsf.org/key4hep/setup.sh
cd '$REPO_ROOT'
source k4ODD/setup.sh
cd k4ODD
export K4ODD_OUTPUT_DIR='$BUCKET_DIR'
$TRACK_ENV

python \$(which k4run) k4ODD/options/ODDreconstruction.py \
  --inputFile '$RECO_INPUT' \
  --outputFile '$BUCKET_DIR/reco.root' \
  > '$BUCKET_DIR/reco.log' 2>&1

case '$ANALYSER' in
  pfo_performance)
    python ci/analyse_pfo_performance.py \
      -i '$BUCKET_DIR/reco.root' -o '$BUCKET_DIR/pfo.root' \
      > '$BUCKET_DIR/analyse.log' 2>&1
    ;;
  gamma_conversion)
    python ci/analyse_pfo_gamma_conversion.py \
      -i '$BUCKET_DIR/reco.root' --plots-dir '$BUCKET_DIR/plots' \
      > '$BUCKET_DIR/analyse.log' 2>&1
    ;;
  none)
    echo 'analyser=none — skipping' > '$BUCKET_DIR/analyse.log'
    ;;
  *)
    echo 'unknown analyser: $ANALYSER' >&2
    exit 2
    ;;
esac
"
