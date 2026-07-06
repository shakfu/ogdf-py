#!/usr/bin/env bash
#
# Shallow-clone OGDF at a pinned release tag and build its static libraries
# from source. This populates thirdparty/ogdf so the extension can link against
# libOGDF.a / libCOIN.a. Run once per machine (or per CI platform); rebuilds of
# the Python bindings then only recompile _core.cpp.
#
# Usage:
#   scripts/bootstrap_ogdf.sh [--tag TAG] [--jobs N] [--force] [--clone-only]
#
# Options:
#   --tag TAG       OGDF git tag to pin to (default: $OGDF_TAG or foxglove-202510)
#   --jobs N        Parallel build jobs (default: CPU count)
#   --force         Re-clone even if thirdparty/ogdf already exists
#   --clone-only    Clone the source but do not build the libraries
#
# Environment overrides: OGDF_TAG, OGDF_REPO.

set -euo pipefail

OGDF_TAG="${OGDF_TAG:-foxglove-202510}"
OGDF_REPO="${OGDF_REPO:-https://github.com/ogdf/ogdf.git}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_dir="$(cd "$script_dir/.." && pwd)"
src_dir="$root_dir/thirdparty/ogdf"
build_dir="$src_dir/build"

# Default job count: portable across macOS (sysctl) and Linux (nproc).
jobs="$( (sysctl -n hw.ncpu 2>/dev/null) || (nproc 2>/dev/null) || echo 4 )"
force=0
clone_only=0

while [ $# -gt 0 ]; do
    case "$1" in
        --tag) OGDF_TAG="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --force) force=1; shift ;;
        --clone-only) clone_only=1; shift ;;
        -h|--help)
            # Print the header comment block (skip the shebang line).
            sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//'
            exit 0 ;;
        *) echo "error: unknown argument '$1'" >&2; exit 2 ;;
    esac
done

for tool in git cmake; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "error: '$tool' is required but not found in PATH" >&2
        exit 1
    }
done

# --- clone ------------------------------------------------------------------ #
if [ -f "$src_dir/CMakeLists.txt" ] && [ "$force" -eq 0 ]; then
    echo "==> OGDF source already present at thirdparty/ogdf (use --force to re-clone)"
else
    echo "==> Cloning OGDF @ $OGDF_TAG (shallow) into thirdparty/ogdf"
    rm -rf "$src_dir"
    git clone --depth 1 --branch "$OGDF_TAG" "$OGDF_REPO" "$src_dir"
fi

if [ "$clone_only" -eq 1 ]; then
    echo "==> Clone complete (--clone-only); skipping build."
    exit 0
fi

# --- build ------------------------------------------------------------------ #
# Only the library targets (COIN + OGDF); PIC so the static objects can be
# linked into the shared Python extension.
echo "==> Configuring OGDF (Release, library targets only)"
cmake -S "$src_dir" -B "$build_dir" \
    -DCMAKE_BUILD_TYPE=Release \
    -DOGDF_LIBRARY_TARGETS_ONLY=ON \
    -DOGDF_WARNING_ERRORS=OFF \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON

echo "==> Building OGDF with $jobs job(s)"
cmake --build "$build_dir" --config Release --parallel "$jobs" --target OGDF COIN

echo "==> Done. Built:"
ls -lh "$build_dir/libOGDF.a" "$build_dir/libCOIN.a"
