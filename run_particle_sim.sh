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

usage() {
  cat <<'EOF'
Usage:
  bash run_particle_sim.sh <particle> <part_index> [events] [eta]

Examples:
  bash run_particle_sim.sh gamma 1
  bash run_particle_sim.sh neutron 3 2000
  bash run_particle_sim.sh kaon0L 4 2000 0

Arguments:
  particle     DD4hep gun particle name, e.g. gamma, neutron, kaon0L
  part_index   Training shard index, used in file name and random seed
  events       Number of events, default: 2000
  eta          Fixed eta value, default: 0

This script mirrors the photon-training gun setup:
  momentum uniformly distributed from 0.2 to 50 GeV
  eta fixed to the chosen value

The output file name is generated automatically as:
  <particle>_train_part<part_index>.root
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 ]]; then
  usage >&2
  exit 1
fi

particle="$1"
part_index="$2"
events="${3:-2000}"
eta="${4:-0}"
seed="$((1000 + part_index))"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$repo_root/setup.sh"

safe_eta="${eta//./p}"
output_dir="${K4ODD_OUTPUT_DIR:-$repo_root}"
mkdir -p "$output_dir"
output_file="$output_dir/${particle}_train_part${part_index}.root"

echo "Running simulation:"
echo "  particle: $particle"
echo "  momentum range: 0.2 to 50 GeV"
echo "  events: $events"
echo "  seed: $seed"
echo "  eta: $eta"
echo "  output: $output_file"

ddsim \
  --steeringFile "$repo_root/k4ODD/options/ODDsimulation.py" \
  --enableGun \
  --gun.distribution uniform \
  --gun.etaMin "$eta" \
  --gun.etaMax "$eta" \
  --gun.momentumMin "0.2*GeV" \
  --gun.momentumMax "50*GeV" \
  --gun.particle "$particle" \
  --numberOfEvents "$events" \
  --outputFile "$output_file" \
  --random.seed "$seed"

echo "Finished: $output_file"
