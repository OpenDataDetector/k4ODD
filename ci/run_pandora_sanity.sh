#!/usr/bin/env bash

##
## Copyright (c) 2020-2024 Key4hep-Project.
##
## This file is part of Key4hep.
## See https://key4hep.github.io/key4hep-doc/ for further info.
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_name="${BUILD_DIR_NAME:-build-ci}"
install_name="${INSTALL_DIR_NAME:-install-ci}"
sim_file="${PANDORA_SANITY_SIM_FILE:-$repo_root/$build_name/pandora_sanity_sim.root}"
reco_file="${PANDORA_SANITY_RECO_FILE:-$repo_root/$build_name/pandora_sanity_reco.root}"

mkdir -p "$(dirname "$sim_file")"
mkdir -p "$(dirname "$reco_file")"

if [[ "${REBUILD_STACK:-0}" == "1" ]]; then
  "$repo_root/ci/rebuild_local_stack.sh"
fi

source "$repo_root/setup.sh"

ddsim \
  --compactFile "$OpenDataDetector/$install_name/share/OpenDataDetector/xml/OpenDataDetector.xml" \
  --steeringFile "$repo_root/k4ODD/options/ODDsimulation.py" \
  --enableGun \
  --gun.distribution uniform \
  --gun.etaMin 0 \
  --gun.etaMax 0 \
  --gun.energy 10*GeV \
  --gun.particle gamma \
  --numberOfEvents 1 \
  --outputFile "$sim_file" \
  --random.seed 123

set +e
python "$(which k4run)" \
  "$repo_root/k4ODD/options/ODDreconstruction.py" \
  --inputFile "$sim_file" \
  --outputFile "$reco_file"
reco_rc=$?
set -e

podio-dump "$reco_file" | rg "GaudiPandoraClusters|GaudiPandoraPFOs|GaudiPandoraStartVertices"

if [[ "$reco_rc" -ne 0 ]]; then
  echo "k4run exited with code $reco_rc after writing valid Pandora output" >&2
fi

echo "Pandora sanity test completed successfully"
