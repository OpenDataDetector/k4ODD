#!/usr/bin/env bash
# Rebuild the INSTRUMENTED PandoraSDK (per-algorithm self-time profiler) from OtherLibraries/PandoraSDK_src.
# CMakeLists is pre-edited to: bypass packaging macros, set SOVERSION 03.04 (matches runtime), and now
# build with -O2 -g (RelWithDebInfo-equivalent) so the instrumented lib is NOT 12x slower than stock at
# scale. SONAME-matched LD_PRELOAD injection (RPATH beats LD_LIBRARY_PATH). Node-local /tmp build.
# Run INSIDE shifter on a compute node.
set -o pipefail
SRC="${PANDORASDK_SRC:?set PANDORASDK_SRC to a PandoraSDK checkout (OpenDataDetector/PandoraSDK @ colliderml/v03-04-01-timing)}"
LB=/tmp/pandorasdk-build
export TMPDIR=/tmp XDG_CACHE_HOME=/tmp/.cache HOME=/tmp/.bh
mkdir -p "$XDG_CACHE_HOME" "$HOME"
[ -d "$LB" ] && find "$LB" -mindepth 1 -delete 2>/dev/null
mkdir -p "$LB"
source /cvmfs/sw.hsf.org/key4hep/setup.sh >/dev/null 2>&1
echo "[psdk] cmake=$(command -v cmake)"
if ! cmake -S "$SRC" -B "$LB" -GNinja > "$LB/configure.log" 2>&1; then
    echo "[psdk] CONFIGURE FAILED:"; tail -25 "$LB/configure.log"; exit 1
fi
if ! cmake --build "$LB" -j8 > "$LB/build.log" 2>&1; then
    echo "[psdk] BUILD FAILED:"; grep -iE 'error:|Error|fatal' "$LB/build.log" | head -25; exit 1
fi
LIB=$(find "$LB" -name 'libPandoraSDK.so.03.04*' -not -type l | head -1)
echo "[psdk] DONE: $LIB"; ls -la "$LB"/libPandoraSDK.so* 2>/dev/null
echo "[psdk] opt level check (should show -O2):"; grep -o '\-O[0-3]' "$LB/build.log" | sort | uniq -c | head
