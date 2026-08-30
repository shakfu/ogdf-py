"""Diagnostic report for the installed extension (`ogdf.about()`).

Answers the questions that come up when a native package misbehaves: which
package version is loaded, which OGDF it was built against, on what platform,
with which compiler, and which capabilities the build exposes.
"""

from __future__ import annotations

import platform
import sys
from typing import Any

from ogdf import _core

# Names that are neither algorithms nor types but appear in the module namespace.
_NON_CAPABILITY = frozenset({"build_info"})


def _capabilities() -> dict[str, list[str]]:
    """Group the exported names into capability buckets.

    Classification is by shape rather than a hand-maintained list, so a newly
    bound layout or generator shows up in `about()` without a second edit:
    layouts are classes whose name ends in "Layout"/"Mixer", other classes are
    types, and the remaining callables are grouped by their I/O prefixes.
    """
    layouts: list[str] = []
    types: list[str] = []
    io: list[str] = []
    functions: list[str] = []
    for name in sorted(n for n in dir(_core) if not n.startswith("_")):
        if name in _NON_CAPABILITY:
            continue
        obj = getattr(_core, name)
        if isinstance(obj, type):
            if name.endswith(("Layout", "Mixer")):
                layouts.append(name)
            else:
                types.append(name)
        elif callable(obj):
            if name.startswith(("read", "write", "draw", "to_")):
                io.append(name)
            else:
                functions.append(name)
    return {"layouts": layouts, "types": types, "io": io, "functions": functions}


def about() -> dict[str, Any]:
    """Return a diagnostic report about this installation.

    Includes the package and OGDF versions, the pinned OGDF tag the linked
    static libraries were built from, platform and interpreter details, the
    compiler used, and a summary of the exposed capabilities.

    >>> import ogdf
    >>> ogdf.about()["package_version"] == ogdf.__version__
    True
    >>> print(ogdf.about_text())                     # doctest: +SKIP
    """
    info: dict[str, Any] = dict(_core.build_info())
    info["python_version"] = platform.python_version()
    info["python_implementation"] = platform.python_implementation()
    info["platform"] = platform.platform()
    info["machine"] = platform.machine()
    info["extension_path"] = getattr(_core, "__file__", None)
    caps = _capabilities()
    info["capabilities"] = {name: len(items) for name, items in caps.items()}
    info["capability_names"] = caps
    return info


def about_text() -> str:
    """Return `about()` formatted as a human-readable report.

    This is what `python -m ogdf` prints; paste it into a bug report.
    """
    info = about()
    caps = info["capabilities"]
    lines = [
        "ogdf-py installation report",
        "",
        f"  package version    : {info['package_version']}",
        f"  OGDF version       : {info['ogdf_version']} (pinned tag: {info['ogdf_tag']})",
        f"  OGDF system        : {info['ogdf_system']}",
        f"  OGDF LP solver     : {info['ogdf_lp_solver']}",
        f"  OGDF memory manager: {info['ogdf_memory_manager']}",
        f"  OGDF debug build   : {info['ogdf_debug_build']}",
        "",
        f"  python             : {info['python_implementation']} {info['python_version']}",
        f"  platform           : {info['platform']} ({info['machine']})",
        f"  compiler           : {info['compiler']}",
        f"  extension          : {info['extension_path']}",
        "",
        "  capabilities       : "
        f"{caps['layouts']} layouts, {caps['functions']} algorithms/generators, "
        f"{caps['io']} I/O functions, {caps['types']} types",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m ogdf`: print the installation report."""
    del argv
    print(about_text())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
