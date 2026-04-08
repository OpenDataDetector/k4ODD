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
stack_setup="${KEY4HEP_SETUP:-/cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh}"
build_name="${BUILD_DIR_NAME:-build-ci}"
install_name="${INSTALL_DIR_NAME:-install-ci}"
jobs="${CMAKE_BUILD_PARALLEL_LEVEL:-4}"

resolve_repo_dir() {
  local explicit="${1:-}"
  shift

  if [[ -n "$explicit" ]]; then
    printf '%s\n' "$explicit"
    return 0
  fi

  local candidate=""
  for candidate in "$@"; do
    if [[ -d "$candidate/.git" ]] || [[ -f "$candidate/CMakeLists.txt" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  echo "Could not find repository directory. Tried: $*" >&2
  return 1
}

build_repo() {
  local src_dir="$1"
  local build_dir="$2"
  local install_dir="$3"

  cmake -S "$src_dir" -B "$build_dir" -GNinja -DCMAKE_INSTALL_PREFIX="$install_dir"
  cmake --build "$build_dir" -j"$jobs"
  cmake --install "$build_dir"
}

had_nounset=0
if [[ $- == *u* ]]; then
  had_nounset=1
  set +u
fi

source "$stack_setup"

if [[ "$had_nounset" -eq 1 ]]; then
  set -u
fi

odd_repo="$(resolve_repo_dir "${ODD_DIR:-}" "$repo_root/OpenDataDetector" "$repo_root/../OpenDataDetector")"
pandora_repo="$(resolve_repo_dir "${K4GAUDIPANDORA_DIR:-}" "$repo_root/../k4GaudiPandora" "$repo_root/k4GaudiPandora")"

if [[ ! -d "$pandora_repo" ]]; then
  echo "Missing k4GaudiPandora repo: $pandora_repo" >&2
  exit 1
fi

build_repo "$odd_repo" "$odd_repo/$build_name" "$odd_repo/$install_name"
build_repo "$pandora_repo" "$pandora_repo/$build_name" "$pandora_repo/$install_name"

cd "$pandora_repo"
k4_local_repo "$install_name" >/dev/null
cd "$repo_root"
build_repo "$repo_root" "$repo_root/$build_name" "$repo_root/$install_name"

echo "Rebuilt OpenDataDetector, k4GaudiPandora, and k4ODD into $install_name"
