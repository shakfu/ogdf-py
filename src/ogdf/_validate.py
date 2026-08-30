"""Precondition inspection: what an operation needs, and what a graph provides.

The bindings enforce documented preconditions at the call site and raise
`InvalidGraphError`. That tells a caller what went wrong *after* the fact; the
helpers here let them ask beforehand, and get a report instead of an exception:

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 5)
    >>> ogdf.requirements("TutteLayout")
    ('at least 3 nodes', 'planar', 'triconnected')
    >>> ogdf.validate("TutteLayout", g)
    ['planar']
    >>> ogdf.is_valid_for("TutteLayout", g)
    False

The requirement table mirrors the checks compiled into the bindings, so
`validate()` returning an empty list and the call succeeding mean the same
thing.
"""

from __future__ import annotations

from typing import Any, Callable

from ogdf import _core

# Each property is a (human-readable description, predicate) pair. Descriptions
# are what `requirements()` and `validate()` report, so they read as the tail of
# "<operation> requires ...".
_PROPERTIES: dict[str, tuple[str, Callable[[Any], bool]]] = {
    "non_empty": ("a non-empty graph", lambda g: g.number_of_nodes() > 0),
    "min_nodes_2": ("at least 2 nodes", lambda g: g.number_of_nodes() >= 2),
    "min_nodes_3": ("at least 3 nodes", lambda g: g.number_of_nodes() >= 3),
    "simple": (
        "simple (no self-loops or parallel edges)",
        _core.is_simple_undirected,
    ),
    "connected": ("connected", _core.is_connected),
    "biconnected": ("biconnected", _core.is_biconnected),
    "triconnected": ("triconnected", _core.is_triconnected),
    "planar": ("planar", _core.is_planar),
    "planar_embedded": (
        "a planar embedding (call planar_embed first)",
        _core.represents_comb_embedding,
    ),
    "acyclic": ("acyclic when edges are read as directed", _core.is_acyclic),
    "forest": ("a tree or forest", _core.is_forest),
    "tree": ("a tree (connected and acyclic)", _core.is_tree),
    "bipartite": ("bipartite", _core.is_bipartite),
}

# The preconditions each operation checks. Keys are the public API names; the
# order is the order in which the binding checks them, so `validate()` lists
# violations in the order a caller would hit them.
_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    # Planar grid layouts.
    "SchnyderLayout": ("min_nodes_3", "simple", "planar"),
    "FPPLayout": ("min_nodes_3", "simple", "planar"),
    "PlanarStraightLayout": ("min_nodes_3", "simple", "planar"),
    "PlanarDrawLayout": ("min_nodes_3", "simple", "planar"),
    "MixedModelLayout": ("min_nodes_3", "simple", "planar"),
    "TutteLayout": ("min_nodes_3", "planar", "triconnected"),
    # Tree layouts.
    "TreeLayout": ("forest",),
    "RadialTreeLayout": ("tree",),
    "BalloonLayout": ("connected",),
    # Upward drawings for DAGs.
    "DominanceLayout": ("non_empty", "acyclic"),
    "VisibilityLayout": ("non_empty", "acyclic"),
    # Force-directed.
    "SpringEmbedderKK": ("connected",),
    # Algorithms.
    "topological_numbering": ("acyclic",),
    "triangulate": ("min_nodes_3", "simple", "connected", "planar_embedded"),
    "min_cut": ("min_nodes_2",),
    "maximum_matching_bipartite": ("bipartite",),
    "spqr_tree_summary": ("min_nodes_3", "biconnected"),
}


def _known(name: str) -> tuple[str, ...]:
    try:
        return _REQUIREMENTS[name]
    except KeyError:
        raise KeyError(
            f"no recorded graph preconditions for {name!r}; "
            f"known operations: {', '.join(sorted(_REQUIREMENTS))}"
        ) from None


def operations() -> tuple[str, ...]:
    """Every operation with recorded graph preconditions, sorted by name.

    Operations absent from this list place no structural requirement on their
    input beyond the argument checks every binding performs (non-null nodes,
    arrays belonging to the right graph, non-negative weights).
    """
    return tuple(sorted(_REQUIREMENTS))


def requirements(name: str) -> tuple[str, ...]:
    """The graph properties `name` requires, as human-readable phrases.

    Raises `KeyError` if the operation has no recorded preconditions; use
    `operations()` for the list of those that do.
    """
    return tuple(_PROPERTIES[key][0] for key in _known(name))


def validate(name: str, graph: Any) -> list[str]:
    """Return the requirements of `name` that `graph` does not satisfy.

    An empty list means the call will not be rejected for structural reasons.
    Checks run in the order the binding checks them and stop at nothing, so a
    graph that fails several requirements reports all of them.
    """
    return [
        _PROPERTIES[key][0] for key in _known(name) if not _PROPERTIES[key][1](graph)
    ]


def is_valid_for(name: str, graph: Any) -> bool:
    """True if `graph` satisfies every recorded precondition of `name`."""
    return not validate(name, graph)


def check(name: str, graph: Any) -> None:
    """Raise `InvalidGraphError` if `graph` fails a precondition of `name`.

    The same error the operation itself would raise, but without running it -
    useful for validating a batch of inputs up front.
    """
    unmet = validate(name, graph)
    if unmet:
        raise _core.InvalidGraphError(f"{name} requires {', '.join(unmet)}")


def graph_report(graph: Any) -> dict[str, Any]:
    """Describe a graph's structural properties in one call.

    Returns node/edge counts alongside every property in the requirement
    vocabulary, so a user can see at a glance why an algorithm rejected their
    input. Some properties are non-trivial to compute (planarity,
    triconnectivity), so this is a diagnostic rather than something to call in
    a loop.
    """
    report: dict[str, Any] = {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }
    for key, (_, predicate) in _PROPERTIES.items():
        report[key] = bool(predicate(graph))
    return report
