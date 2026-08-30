#!/usr/bin/env python3
"""Obtain OGDF at a pinned release tag and build its static libraries from source.

Cross-platform (Linux, macOS, Windows); uses only the Python standard library.
This populates ``thirdparty/ogdf`` so the extension can link against the OGDF and
COIN static libraries. Run once per machine (or per CI platform); rebuilds of the
Python bindings then only recompile the binding sources.

The source can come from a shallow git clone (the default) or, for offline and
reproducible-build environments, from a local source archive or an existing
checkout. See ``--archive`` / ``--source-dir`` and the matching environment
variables.

Usage:
    python scripts/bootstrap_ogdf.py [--tag TAG] [--jobs N] [--force]
                                     [--clone-only] [--archive PATH]
                                     [--source-dir PATH] [--offline]

Environment overrides:
    OGDF_TAG        git tag to clone (default: contents of scripts/ogdf-tag.txt)
    OGDF_REPO       git remote to clone from
    OGDF_ARCHIVE    path to a local OGDF source archive (.zip/.tar.gz/.tar.bz2)
    OGDF_SOURCE_DIR path to an existing OGDF source tree to copy from
    OGDF_OFFLINE    set to 1 to forbid network access (no clone)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "thirdparty" / "ogdf"
BUILD = SRC / "build"
TAG_FILE = Path(__file__).resolve().parent / "ogdf-tag.txt"


def pinned_tag() -> str:
    """The OGDF tag this project is pinned to.

    Single source of truth for the tag: ``scripts/ogdf-tag.txt``, which CMake
    also reads so ``ogdf.about()`` can report the tag the extension was built
    against.
    """
    if "OGDF_TAG" in os.environ:
        return os.environ["OGDF_TAG"]
    try:
        return TAG_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "foxglove-202510"


DEFAULT_TAG = pinned_tag()
OGDF_REPO = os.environ.get("OGDF_REPO", "https://github.com/ogdf/ogdf.git")


def run(cmd: list[str]) -> None:
    print("==>", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def fail(problem: str, hint: str) -> None:
    """Exit with a message that names the failing stage and how to fix it."""
    sys.exit(f"error: {problem}\nhint: {hint}")


def library_paths() -> list[Path]:
    """Candidate locations of the built OGDF static library, per platform."""
    if os.name == "nt":
        # MSVC single- or multi-config (Visual Studio puts it under Release/).
        return [BUILD / "OGDF.lib", BUILD / "Release" / "OGDF.lib"]
    return [BUILD / "libOGDF.a"]


def already_built() -> bool:
    return any(p.exists() for p in library_paths())


def _strip_single_root(extracted: Path, dest: Path) -> None:
    """Move an extracted tree into `dest`, unwrapping a single top-level dir.

    Source archives from GitHub wrap everything in `ogdf-<tag>/`; a hand-rolled
    archive may not. Handle both so `dest/CMakeLists.txt` ends up in place.
    """
    entries = [p for p in extracted.iterdir() if p.name != "__MACOSX"]
    root = entries[0] if len(entries) == 1 and entries[0].is_dir() else extracted
    if not (root / "CMakeLists.txt").exists():
        fail(
            f"archive does not look like an OGDF source tree "
            f"(no CMakeLists.txt under {root})",
            "point --archive at an OGDF source archive, not a binary release.",
        )
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(root), str(dest))


def unpack_archive(archive: Path) -> None:
    """Populate `SRC` from a local source archive (no network needed)."""
    if not archive.exists():
        fail(f"archive not found: {archive}", "check the --archive/OGDF_ARCHIVE path.")
    staging = SRC.parent / "_ogdf_unpack"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    print(f"==> Unpacking {archive} into {SRC}")
    name = archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(staging)
    elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".tar")):
        with tarfile.open(archive) as tf:
            tf.extractall(staging)
    else:
        shutil.rmtree(staging)
        fail(
            f"unsupported archive format: {archive.name}",
            "use .zip, .tar.gz, .tar.bz2, .tar.xz, or .tar.",
        )
    try:
        _strip_single_root(staging, SRC)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def copy_source_dir(source: Path) -> None:
    """Populate `SRC` by copying an existing OGDF checkout (no network needed)."""
    if not (source / "CMakeLists.txt").exists():
        fail(
            f"{source} is not an OGDF source tree (no CMakeLists.txt)",
            "point --source-dir/OGDF_SOURCE_DIR at an OGDF checkout.",
        )
    print(f"==> Copying OGDF source from {source} into {SRC}")
    if SRC.exists():
        shutil.rmtree(SRC)
    shutil.copytree(source, SRC, symlinks=True)


def clone(tag: str, offline: bool) -> None:
    if offline:
        fail(
            "OGDF source is missing and network access is disabled",
            "supply the source locally with --archive PATH or --source-dir PATH "
            "(or OGDF_ARCHIVE / OGDF_SOURCE_DIR), or drop --offline/OGDF_OFFLINE.",
        )
    if shutil.which("git") is None:
        fail(
            "'git' is required to clone OGDF but was not found in PATH",
            "install git, or avoid cloning with --archive PATH / --source-dir PATH.",
        )
    print(f"==> Cloning OGDF @ {tag} (shallow) into {SRC}")
    if SRC.exists():
        shutil.rmtree(SRC)
    try:
        run(["git", "clone", "--depth", "1", "--branch", tag, OGDF_REPO, str(SRC)])
    except subprocess.CalledProcessError as exc:
        fail(
            f"git clone of {OGDF_REPO} @ {tag} failed (exit {exc.returncode})",
            "check network/proxy access to the remote, or vendor the source with "
            "--archive PATH / --source-dir PATH for an offline build.",
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Obtain OGDF at a pinned tag and build it from source."
    )
    parser.add_argument(
        "--tag", default=DEFAULT_TAG, help=f"OGDF git tag (default: {DEFAULT_TAG})"
    )
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 4, help="parallel build jobs"
    )
    parser.add_argument(
        "--force", action="store_true", help="re-fetch even if thirdparty/ogdf exists"
    )
    parser.add_argument(
        "--clone-only", action="store_true", help="fetch the source but do not build"
    )
    parser.add_argument(
        "--archive",
        default=os.environ.get("OGDF_ARCHIVE"),
        help="local OGDF source archive to unpack instead of cloning",
    )
    parser.add_argument(
        "--source-dir",
        default=os.environ.get("OGDF_SOURCE_DIR"),
        help="existing OGDF source tree to copy instead of cloning",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=os.environ.get("OGDF_OFFLINE", "") not in ("", "0"),
        help="forbid network access; fail instead of cloning",
    )
    args = parser.parse_args(argv)

    if shutil.which("cmake") is None:
        fail(
            "'cmake' is required but was not found in PATH",
            "install CMake >= 3.15 (e.g. `pip install cmake`) and retry.",
        )

    # --- obtain the source: existing checkout, archive, copy, or clone --- #
    if (SRC / "CMakeLists.txt").exists() and not args.force:
        print(f"==> OGDF source already present at {SRC} (use --force to re-fetch)")
    elif args.archive:
        unpack_archive(Path(args.archive).expanduser().resolve())
    elif args.source_dir:
        copy_source_dir(Path(args.source_dir).expanduser().resolve())
    else:
        clone(args.tag, args.offline)

    if args.clone_only:
        print("==> Source ready (--clone-only); skipping build.")
        return

    # --- configure + build (library targets only; PIC for shared linking) --- #
    print("==> Configuring OGDF (Release, library targets only)")
    try:
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
    except subprocess.CalledProcessError as exc:
        fail(
            f"CMake configuration of OGDF failed (exit {exc.returncode})",
            "this usually means no working C++17 compiler was found. Install one "
            "(g++/clang++/MSVC Build Tools) and see the CMake output above.",
        )

    print(f"==> Building OGDF with {args.jobs} job(s)")
    try:
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
    except subprocess.CalledProcessError as exc:
        fail(
            f"compiling OGDF failed (exit {exc.returncode})",
            "see the compiler output above; a C++17 compiler and roughly 2 GB of "
            "free disk space are required.",
        )

    built = [p for p in library_paths() if p.exists()]
    if not built:
        fail(
            "the build finished but no OGDF library was produced",
            f"expected one of: {', '.join(str(p) for p in library_paths())}",
        )
    print("==> Done. Built:")
    for path in built:
        print(f"    {path}  ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
