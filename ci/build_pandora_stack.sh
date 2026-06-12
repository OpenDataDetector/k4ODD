#!/usr/bin/env bash
# Build the pinned Pandora particle-flow stack (PandoraSDK -> LCContent -> k4GaudiPandora ->
# k4DetectorPerformance) at the refs in ci/pandora_stack.env, into one install prefix.
#
# Run inside a key4hep environment (CI container with CVMFS, or shifter at NERSC):
#   shifter --image=registry.cern.ch/atlasadc/atlas-grid-almalinux9 --module=cvmfs \
#     bash ci/build_pandora_stack.sh
#
# Outputs:
#   PANDORA_STACK_PREFIX (default ./pandora-stack/install) with lib/, lib64/, python/.
#   Source checkouts cached under PANDORA_STACK_SRC (default ./pandora-stack/src);
#   re-runs reuse them (fetch + checkout ref), so CI can cache the whole pandora-stack dir
#   keyed on the hash of ci/pandora_stack.env.
#
# Notes:
# - Build dirs default to node-local /tmp: CFS/Lustre locking is unreliable for some build
#   tooling (Gaudi genconf .confdb2 sqlite). Override with PANDORA_STACK_BUILD for CI runners.
# - The full coherent stack is built against OUR PandoraSDK (unlike the standalone
#   scripts/build_lccontent.sh LD_PRELOAD flow, which builds against the stock SDK).
# - No `set -u`: key4hep setup.sh references unset variables.
set -eo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/pandora_stack.env"

stack_setup="${KEY4HEP_SETUP:-/cvmfs/sw.hsf.org/key4hep/setup.sh}"
workdir="${PANDORA_STACK_DIR:-$PWD/pandora-stack}"
srcdir="${PANDORA_STACK_SRC:-$workdir/src}"
builddir="${PANDORA_STACK_BUILD:-/tmp/pandora-stack-build}"
prefix="${PANDORA_STACK_PREFIX:-$workdir/install}"
jobs="${CMAKE_BUILD_PARALLEL_LEVEL:-8}"

mkdir -p "$srcdir" "$builddir" "$prefix"
source "$stack_setup" >/dev/null 2>&1
echo "[stack] key4hep: $(command -v k4run || true) ; cmake: $(command -v cmake)"
echo "[stack] prefix:  $prefix"

checkout() { # name repo ref
  local name="$1" repo="$2" ref="$3" dir="$srcdir/$1"
  if [[ ! -d "$dir/.git" ]]; then
    git clone --quiet "$repo" "$dir"
  fi
  git -C "$dir" fetch --quiet --tags --force origin
  git -C "$dir" checkout --quiet "$ref"
  echo "[stack] $name @ $(git -C "$dir" rev-parse --short HEAD) ($ref)"
}

build() { # name [extra cmake args...]
  local name="$1"; shift
  local bd="$builddir/$name"
  mkdir -p "$bd"
  echo "[stack] configure $name"
  # Install-RPATH must put OUR prefix first: Gaudi/key4hep bake DT_RPATH into plugins, and
  # RPATH beats LD_LIBRARY_PATH — without this, libPandoraSDK resolves back to the cvmfs one.
  if ! cmake -S "$srcdir/$name" -B "$bd" -GNinja \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_INSTALL_PREFIX="$prefix" \
        -DCMAKE_PREFIX_PATH="$prefix;${CMAKE_PREFIX_PATH//:/;}" \
        -DCMAKE_INSTALL_RPATH="$prefix/lib;$prefix/lib64" \
        -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON \
        "$@" > "$bd/configure.log" 2>&1; then
    echo "[stack] $name CONFIGURE FAILED:"; tail -30 "$bd/configure.log"; exit 1
  fi
  echo "[stack] build $name"
  if ! cmake --build "$bd" -j"$jobs" --target install > "$bd/build.log" 2>&1; then
    echo "[stack] $name BUILD FAILED:"; grep -iE 'error:|Error|fatal' "$bd/build.log" | head -25; exit 1
  fi
}

checkout PandoraSDK "$PANDORASDK_REPO" "$PANDORASDK_REF"
checkout LCContent "$LCCONTENT_REPO" "$LCCONTENT_REF"
checkout k4GaudiPandora "$K4GAUDIPANDORA_REPO" "$K4GAUDIPANDORA_REF"
checkout k4DetectorPerformance "$K4DETPERFORMANCE_REPO" "$K4DETPERFORMANCE_REF"

build PandoraSDK
build LCContent -DPandoraSDK_DIR="$prefix"
build k4GaudiPandora
build k4DetectorPerformance

echo "[stack] install tree:"
find "$prefix/lib" "$prefix/lib64" -maxdepth 1 \( -name 'libPandoraSDK*' -o -name 'libLCContent*' -o -name '*k4GaudiPandora*' -o -name '*PFlowValidation*' -o -name '*RecoMCTruthLinkers*' \) 2>/dev/null

cat > "$prefix/setup_stack.sh" << EOF
# source AFTER the key4hep setup to put the pinned Pandora stack first.
# No LD_PRELOAD here: the whole stack (k4GaudiPandora plugins included) is built against
# the pinned SDK/LCContent, so LD_LIBRARY_PATH ordering resolves them. (Preloading
# libLCContent globally breaks unrelated binaries — it needs PandoraSDK symbols. The
# preload trick is only for injecting the optimized lib into a STOCK cvmfs k4GaudiPandora;
# see scripts/build_lccontent.sh for that flow.)
export PANDORA_STACK_PREFIX="$prefix"
export CMAKE_PREFIX_PATH="$prefix:\$CMAKE_PREFIX_PATH"
export LD_LIBRARY_PATH="$prefix/lib:$prefix/lib64:\$LD_LIBRARY_PATH"
export PYTHONPATH="$prefix/python:\$PYTHONPATH"
EOF
echo "[stack] DONE. source $prefix/setup_stack.sh after the key4hep setup."
