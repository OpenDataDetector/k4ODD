#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Source this script instead of executing it: source setup.sh" >&2
  exit 1
fi

set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
stack_setup="${KEY4HEP_SETUP:-/cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh}"

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

find_install_dir() {
  local repo="$1"
  local found=""

  while IFS= read -r candidate; do
    found="$candidate"
    break
  done < <(find "$repo" -maxdepth 1 -mindepth 1 -type d \( -name 'install-*' -o -name 'install' \) -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk '{print $2}')

  if [[ -z "$found" ]]; then
    echo "No install directory found under $repo" >&2
    return 1
  fi

  printf '%s\n' "$found"
}

had_nounset=0
if [[ $- == *u* ]]; then
  had_nounset=1
  set +u
fi

source "$stack_setup"

odd_repo="$(resolve_repo_dir "${ODD_DIR:-}" "$repo_root/OpenDataDetector" "$repo_root/../OpenDataDetector")"
pandora_repo="$(resolve_repo_dir "${K4GAUDIPANDORA_DIR:-}" "$repo_root/../k4GaudiPandora" "$repo_root/k4GaudiPandora")"

odd_install_dir="${ODD_INSTALL_DIR:-$(find_install_dir "$odd_repo")}"
repo_install_dir="${K4ODD_INSTALL_DIR:-$(find_install_dir "$repo_root")}"
pandora_install_dir="${K4GAUDIPANDORA_INSTALL_DIR:-$(find_install_dir "$pandora_repo")}"

export OpenDataDetector="$odd_repo"
source "$odd_install_dir/bin/this_odd.sh"

setup_pwd="$PWD"
cd "$pandora_repo"
k4_local_repo "$(basename "$pandora_install_dir")" >/dev/null
cd "$repo_root"
k4_local_repo "$(basename "$repo_install_dir")" >/dev/null
cd "$setup_pwd"

export K4ODD_PANDORA_SETTINGS="${K4ODD_PANDORA_SETTINGS:-$repo_root/k4ODD/options/PandoraSettingsSanity.xml}"

if [[ "$had_nounset" -eq 1 ]]; then
  set -u
fi

echo "Key4hep stack: $KEY4HEP_STACK"
echo "OpenDataDetector install: $odd_install_dir"
echo "k4GaudiPandora install: $pandora_install_dir"
echo "k4ODD install: $repo_install_dir"
echo "Pandora settings: $K4ODD_PANDORA_SETTINGS"
