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

The pinned tag must resolve to the commit in ``scripts/ogdf-commit.txt``; a
clone that does not is rejected, since a moved tag would change the code linked
into published wheels. An existing checkout that no longer matches the pin
(after a tag bump) is re-fetched.

Environment overrides:
    OGDF_TAG        git tag to clone (default: contents of scripts/ogdf-tag.txt);
                    the commit pin does not apply to an overridden tag
    OGDF_REPO       git remote to clone from
    OGDF_ARCHIVE    path to a local OGDF source archive (.zip/.tar.gz/.tar.bz2)
    OGDF_SOURCE_DIR path to an existing OGDF source tree to copy from
    OGDF_OFFLINE    set to 1 to forbid network access (no clone)
    OGDF_ARCH       -march value for GCC/Clang (default: the ISA baseline,
                    x86-64 or armv8-a; "native" tunes for the build machine)
"""

from __future__ import annotations

import argparse
import os
import platform
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
COMMIT_FILE = Path(__file__).resolve().parent / "ogdf-commit.txt"
# Records where SRC came from: "clone <tag>", "archive <path>" or
# "source-dir <path>".
STAMP = SRC / ".ogdfpy-source"


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


def pinned_commit(tag: str) -> str | None:
    """The commit `tag` must resolve to, or None for an overridden tag."""
    try:
        file_tag = TAG_FILE.read_text(encoding="utf-8").strip()
        commit = COMMIT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return commit if tag == file_tag else None


OGDF_REPO = os.environ.get("OGDF_REPO", "https://github.com/ogdf/ogdf.git")


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(SRC), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def checkout_matches(tag: str) -> bool:
    """True if the git checkout at SRC is the commit `tag` is pinned to."""
    if shutil.which("git") is None or not (SRC / ".git").exists():
        return False
    head = git_output("rev-parse", "HEAD")
    commit = pinned_commit(tag)
    if commit is not None:
        return head == commit
    return tag in git_output("tag", "--points-at", "HEAD").split()


def source_is_current(tag: str) -> bool:
    """Whether the source already at SRC can be used for `tag`.

    Sources supplied with --archive or --source-dir are the caller's choice and
    are used as they are. A clone, or a checkout from before the stamp existed,
    must match the pin.
    """
    try:
        stamp = STAMP.read_text(encoding="utf-8").split()
    except OSError:
        stamp = []
    if stamp and stamp[0] in ("archive", "source-dir"):
        return True
    return checkout_matches(tag)


def write_stamp(kind: str, detail: str) -> None:
    STAMP.write_text(f"{kind} {detail}\n", encoding="utf-8")


def target_arch() -> str | None:
    """The -march value to build OGDF for, or None to leave OGDF's choice.

    OGDF defaults to -march=native on GCC/Clang outside ^arm processors, so a
    library built on a CI runner can use instructions an older CPU lacks: a
    cached build crashed another runner with SIGILL, and wheels would crash
    users' machines the same way. Default to the ISA baseline instead.
    """
    if "OGDF_ARCH" in os.environ:
        return os.environ["OGDF_ARCH"]
    if os.name == "nt":
        return None  # MSVC ignores OGDF_ARCH
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86-64"
    if machine in ("aarch64", "arm64"):
        return "armv8-a"
    return None


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


def safe_extract(tf: tarfile.TarFile, dest: Path) -> None:
    """Extract without letting a member write outside `dest`.

    Uses the "data" filter where available (3.10.12+, 3.11.4+, 3.12+); older
    interpreters get an equivalent check of each member's path and link target.
    """
    if hasattr(tarfile, "data_filter"):
        try:
            tf.extractall(dest, filter="data")
        except tarfile.FilterError as exc:
            fail(
                f"unsafe archive member: {exc}",
                "use an unmodified OGDF source archive.",
            )
        return
    root = dest.resolve()
    for member in tf.getmembers():
        target = (root / member.name).resolve()
        link = (
            (target.parent / member.linkname).resolve()
            if member.issym() or member.islnk()
            else target
        )
        for path in (target, link):
            if path != root and root not in path.parents:
                fail(
                    f"archive member {member.name!r} would be written outside "
                    "the extraction directory",
                    "use an unmodified OGDF source archive.",
                )
        if member.isdev():
            fail(
                f"archive member {member.name!r} is a device file",
                "use an unmodified OGDF source archive.",
            )
    tf.extractall(dest)  # noqa: S202 - every member checked above


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
    try:
        if name.endswith(".zip"):
            # zipfile.extractall already drops absolute and ".." components.
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(staging)
        elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".tar")):
            with tarfile.open(archive) as tf:
                safe_extract(tf, staging)
        else:
            fail(
                f"unsupported archive format: {archive.name}",
                "use .zip, .tar.gz, .tar.bz2, .tar.xz, or .tar.",
            )
        _strip_single_root(staging, SRC)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    write_stamp("archive", str(archive))


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
    write_stamp("source-dir", str(source))


def clone(tag: str, offline: bool, stale: bool = False) -> None:
    if offline and stale:
        fail(
            f"the OGDF checkout at {SRC} does not match OGDF @ {tag}, and network "
            "access is disabled",
            "re-fetch it with network access, or supply the matching source with "
            "--archive PATH or --source-dir PATH (or OGDF_ARCHIVE / "
            "OGDF_SOURCE_DIR).",
        )
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
    if not checkout_matches(tag):
        head = git_output("rev-parse", "HEAD")
        expected = pinned_commit(tag) or f"a commit tagged {tag}"
        shutil.rmtree(SRC, ignore_errors=True)
        fail(
            f"{OGDF_REPO} @ {tag} resolved to {head or 'an unknown commit'}, "
            f"not the pinned {expected}",
            "the tag was moved or the remote is not the official one. If the "
            "change is intended, update scripts/ogdf-commit.txt.",
        )
    write_stamp("clone", tag)


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
    present = (SRC / "CMakeLists.txt").exists()
    if present and not args.force and source_is_current(args.tag):
        print(f"==> OGDF source already present at {SRC} (use --force to re-fetch)")
        if not STAMP.exists():
            write_stamp("clone", args.tag)
    elif args.archive:
        unpack_archive(Path(args.archive).expanduser().resolve())
    elif args.source_dir:
        copy_source_dir(Path(args.source_dir).expanduser().resolve())
    else:
        stale = present and not args.force
        if stale and not args.offline:
            print(f"==> {SRC} does not match OGDF @ {args.tag}; re-fetching")
        clone(args.tag, args.offline, stale=stale)

    if args.clone_only:
        print("==> Source ready (--clone-only); skipping build.")
        return

    # --- configure + build (library targets only; PIC for shared linking) --- #
    arch = target_arch()
    print(
        "==> Configuring OGDF (Release, library targets only"
        + (f", -march={arch})" if arch else ")")
    )
    configure = [
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
    if arch:
        configure.append(f"-DOGDF_ARCH={arch}")
    try:
        run(configure)
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
