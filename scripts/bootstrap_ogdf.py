#!/usr/bin/env python3
"""Clone OGDF at a pinned release tag and build its static libraries from source.

Cross-platform (Linux, macOS, Windows); uses only the Python standard library.
This populates ``thirdparty/ogdf`` so the extension can link against the OGDF and
COIN static libraries. Run once per machine (or per CI platform); rebuilds of the
Python bindings then only recompile the binding sources.

Usage:
    python scripts/bootstrap_ogdf.py [--tag TAG] [--jobs N] [--force]
                                     [--clone-only]

Environment overrides: OGDF_TAG, OGDF_REPO.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TAG = os.environ.get("OGDF_TAG", "foxglove-202510")
OGDF_REPO = os.environ.get("OGDF_REPO", "https://github.com/ogdf/ogdf.git")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "thirdparty" / "ogdf"
BUILD = SRC / "build"


def run(cmd: list[str]) -> None:
    print("==>", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def library_paths() -> list[Path]:
    """Candidate locations of the built OGDF static library, per platform."""
    if os.name == "nt":
        # MSVC single- or multi-config (Visual Studio puts it under Release/).
        return [BUILD / "OGDF.lib", BUILD / "Release" / "OGDF.lib"]
    return [BUILD / "libOGDF.a"]


def already_built() -> bool:
    return any(p.exists() for p in library_paths())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Clone OGDF at a pinned tag and build it from source."
    )
    parser.add_argument(
        "--tag", default=DEFAULT_TAG, help=f"OGDF git tag (default: {DEFAULT_TAG})"
    )
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 4, help="parallel build jobs"
    )
    parser.add_argument(
        "--force", action="store_true", help="re-clone even if thirdparty/ogdf exists"
    )
    parser.add_argument(
        "--clone-only", action="store_true", help="clone the source but do not build"
    )
    args = parser.parse_args(argv)

    for tool in ("git", "cmake"):
        if shutil.which(tool) is None:
            sys.exit(f"error: '{tool}' is required but not found in PATH")

    # --- clone --- #
    if (SRC / "CMakeLists.txt").exists() and not args.force:
        print(f"==> OGDF source already present at {SRC} (use --force to re-clone)")
    else:
        print(f"==> Cloning OGDF @ {args.tag} (shallow) into {SRC}")
        if SRC.exists():
            shutil.rmtree(SRC)
        run(["git", "clone", "--depth", "1", "--branch", args.tag, OGDF_REPO, str(SRC)])

    if args.clone_only:
        print("==> Clone complete (--clone-only); skipping build.")
        return

    # --- configure + build (library targets only; PIC for shared linking) --- #
    print("==> Configuring OGDF (Release, library targets only)")
    run(
        [
            "cmake",
            "-S",
            str(SRC),
            "-B",
            str(BUILD),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DOGDF_LIBRARY_TARGETS_ONLY=ON",
            "-DOGDF_WARNING_ERRORS=OFF",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        ]
    )

    print(f"==> Building OGDF with {args.jobs} job(s)")
    run(
        [
            "cmake",
            "--build",
            str(BUILD),
            "--config",
            "Release",
            "--parallel",
            str(args.jobs),
            "--target",
            "OGDF",
            "COIN",
        ]
    )

    built = [p for p in library_paths() if p.exists()]
    if not built:
        sys.exit("error: build finished but no OGDF library was produced")
    print("==> Done. Built:")
    for path in built:
        print(f"    {path}  ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
