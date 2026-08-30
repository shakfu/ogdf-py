"""Reproducibility: seeding, and provenance metadata for a result.

Several generators, layouts, and heuristics in OGDF are randomized -
`random_graph` and friends, `FMMMLayout`, `GEMLayout`, the multilevel layouts,
and the randomized restarts inside `crossing_number` and `PlanarizationLayout`.

OGDF draws all of that from a single process-wide engine. That is the honest
shape of the underlying library, so this module exposes it as such rather than
pretending each call has a private stream: seed once, and everything downstream
is reproducible.

    >>> import ogdf
    >>> with ogdf.seeded(20260831):
    ...     g = ogdf.Graph()
    ...     ogdf.random_graph(g, 30, 60)

What reproducibility guarantees
-------------------------------
Given the same seed, the same package version, and the same OGDF build, a
sequence of calls produces the same graph and the same coordinates. It is *not*
guaranteed across platforms, compilers, or OGDF versions: floating-point layout
code is sensitive to instruction selection and library math. Record
`provenance()` alongside a result and compare like with like.
"""

from __future__ import annotations

import platform
from contextlib import contextmanager
from typing import Any, Iterator

from ogdf import _core

# The last seed passed to set_seed(), so provenance() can report what a result
# was produced under. OGDF's engine cannot be asked for its current seed, so
# this is bookkeeping rather than a read of the engine.
_current_seed: int | None = None


def set_seed(seed: int) -> int:
    """Seed OGDF's process-wide random engine; returns the seed.

    Affects every randomized generator, layout, and heuristic from this point
    on, in this process.
    """
    global _current_seed
    _core.seed_random_engine(int(seed))
    _current_seed = int(seed)
    return _current_seed


def get_seed() -> int | None:
    """The seed most recently passed to `set_seed`, or None if never seeded.

    None means the engine is running from its default state, so results are
    repeatable within a process run but not across runs.
    """
    return _current_seed


def new_seed() -> int:
    """Draw a fresh seed value, for recording and reusing later.

    Use this to pin down an otherwise unseeded experiment: draw a seed, record
    it in `provenance()`, and pass it to `set_seed`.
    """
    return int(_core.draw_random_seed())


@contextmanager
def seeded(seed: int) -> Iterator[int]:
    """Run a block with OGDF seeded to `seed`; yields the seed.

    On exit the previous seed is re-applied if one was ever set. Because the
    engine cannot be asked for its position, that restores the *seed*, not the
    exact stream state: code after the block sees the same sequence it would
    have seen right after that earlier `set_seed`. Nest carefully.

    >>> import ogdf
    >>> with ogdf.seeded(7):
    ...     g = ogdf.Graph()
    ...     ogdf.random_graph(g, 20, 40)
    >>> g.number_of_edges()
    40
    """
    global _current_seed
    previous = _current_seed
    set_seed(seed)
    try:
        yield seed
    finally:
        if previous is None:
            _current_seed = None
        else:
            set_seed(previous)


def provenance(**settings: Any) -> dict[str, Any]:
    """Metadata describing how a result was produced, ready to serialize.

    Records the seed in effect, the package version, the OGDF version and
    pinned tag, and the platform, plus any algorithm settings passed as keyword
    arguments. Store it next to a drawing or a benchmark row so a later run can
    be compared against like conditions.

    >>> import ogdf
    >>> ogdf.set_seed(42)
    42
    >>> info = ogdf.provenance(algorithm="FMMMLayout", unit_edge_length=20.0)
    >>> info["seed"], info["settings"]["algorithm"]
    (42, 'FMMMLayout')

    The result contains only JSON-serializable values as long as `settings`
    does.
    """
    build = _core.build_info()
    return {
        "seed": _current_seed,
        "package_version": build["package_version"],
        "ogdf_version": build["ogdf_version"],
        "ogdf_tag": build["ogdf_tag"],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "settings": dict(settings),
    }
