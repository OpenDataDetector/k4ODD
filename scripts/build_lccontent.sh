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

# Build a standalone libLCContent.so from OtherLibraries/LCContent_src against the STOCK key4hep
# PandoraSDK, for LD_PRELOAD injection (bounding-sphere FragmentRemoval optimization).
#
# Run INSIDE shifter on a compute node:
#   srun --jobid=<N> --overlap -n1 -c8 \
#     shifter --image=registry.cern.ch/atlasadc/atlas-grid-almalinux9 --module=cvmfs \
#     bash testbed/scripts/build_lccontent.sh <tag>
#
# The runtime libLCContent.so (lccontent/3.2.0) has NO SONAME, so the produced libLCContent.so
# overrides it cleanly via LD_PRELOAD (RPATH beats LD_LIBRARY_PATH, so we must PRELOAD, not path-shadow).
# Node-local /tmp build (CFS/Lustre locking is unreliable for some build tooling). No `set -u`
# (key4hep setup.sh references unset vars).
set -o pipefail
TAG="${1:?tag (e.g. stock|opt)}"
SRC="${LCCONTENT_SRC:?set LCCONTENT_SRC to an LCContent checkout (OpenDataDetector/LCContent @ colliderml/v03-02-00-opt)}"
LB=/tmp/lcc-build-$TAG

export TMPDIR=/tmp XDG_CACHE_HOME=/tmp/.cache HOME=/tmp/.bh
mkdir -p "$XDG_CACHE_HOME" "$HOME"
[ -d "$LB" ] && find "$LB" -mindepth 1 -delete 2>/dev/null
mkdir -p "$LB"

source /cvmfs/sw.hsf.org/key4hep/setup.sh >/dev/null 2>&1
PSDK=$(echo "$CMAKE_PREFIX_PATH" | tr ":" "\n" | grep -i pandorasdk | head -1)
echo "[lcc] tag=$TAG ; PandoraSDK=$PSDK ; cmake=$(command -v cmake)"

echo "[lcc] CONFIGURE"
if ! cmake -S "$SRC" -B "$LB" -GNinja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_INSTALL_PREFIX="$LB/install" > "$LB/configure.log" 2>&1; then
    echo "[lcc] CONFIGURE FAILED:"; tail -30 "$LB/configure.log"; exit 1
fi

echo "[lcc] BUILD"
if ! cmake --build "$LB" -j8 > "$LB/build.log" 2>&1; then
    echo "[lcc] BUILD FAILED:"; grep -iE 'error:|Error|fatal' "$LB/build.log" | head -25; exit 1
fi

LIB=$(find "$LB" -name 'libLCContent.so' -not -path '*/install/*' | head -1)
echo "[lcc] DONE: $LIB"
ls -la "$LIB"
# sanity: our new symbol/strings present in the opt build
[ "$TAG" = "opt" ] && { echo "[lcc] bounding-sphere strings:"; strings "$LIB" | grep -c "bounding sphere\|ClusterBoundingSphere" || true; }
