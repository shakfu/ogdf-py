"""Result objects for algorithms whose answer is more than one number.

The low-level bindings follow OGDF's idiom: the caller allocates a `NodeArray`
or `EdgeArray`, the function fills it, and the return value is a scalar. That is
efficient and stays out of the way in a loop, so it remains available for every
algorithm here.

It also throws information away. `dijkstra` builds a shortest-path tree and
discards it, leaving the caller with distances but no paths; `min_st_cut`
computes the node partition and reports only the cut edges. This module keeps
that work and hands it back with named fields.

Nothing here replaces the array API - the two coexist, and the array form is
what to reach for when you are calling in bulk.
"""

from __future__ import annotations

import math
import sys
from typing import Any, Hashable, Mapping, NamedTuple

from ogdf import _core

__all__ = ["STCut", "ShortestPaths", "min_st_cut", "shortest_paths"]

# The sentinel OGDF writes for an unreachable node, per weight type. The
# ergonomic API converts these to math.inf so callers never compare against a
# magic number.
_UNREACHABLE_FLOAT = sys.float_info.max
_UNREACHABLE_INT = 2**31 - 1


class ShortestPaths:
    """Single-source shortest-path distances *and* the paths themselves.

    Returned by `shortest_paths`. Nodes are addressed by their `Node` handle;
    distances to unreachable nodes are `math.inf` rather than OGDF's raw
    sentinel.

    >>> import ogdf
    >>> g, m = ogdf.from_edges([("a", "b"), ("b", "c"), ("a", "c")])
    >>> paths = ogdf.shortest_paths(g, m["a"])
    >>> paths.distance(m["c"])
    1.0
    >>> len(paths.path_to(m["c"]))
    1
    """

    __slots__ = (
        "_distances",
        "_nodes",
        "_predecessors",
        "algorithm",
        "directed",
        "source",
    )

    def __init__(self, graph, source, distances, predecessors, algorithm, directed):
        nodes = list(graph.nodes())
        #: Keyed by node index - the identity policy the interop layer uses.
        self._nodes: dict[int, Any] = {v.index: v for v in nodes}
        self._distances: dict[int, float] = {}
        self._predecessors: dict[int, Any] = {}
        for v, distance, predecessor in zip(nodes, distances, predecessors):
            unreachable = distance in (_UNREACHABLE_FLOAT, _UNREACHABLE_INT)
            self._distances[v.index] = math.inf if unreachable else float(distance)
            self._predecessors[v.index] = predecessor
        self.source = source
        self.algorithm = algorithm
        self.directed = directed

    # --- distances --------------------------------------------------------- #

    def distance(self, node) -> float:
        """The shortest-path distance to `node`, or `math.inf` if unreachable."""
        return self._distances[node.index]

    def distances(self, *, keys: Mapping[Any, Hashable] | None = None) -> dict:
        """All distances as a dict, keyed by `node.index` or by `keys`."""
        if keys is None:
            return dict(self._distances)
        return {
            keys[self._nodes[index]]: distance
            for index, distance in self._distances.items()
        }

    def reachable(self, node) -> bool:
        """True if a path from the source to `node` exists."""
        return not math.isinf(self._distances[node.index])

    def reachable_nodes(self) -> list:
        """Every node reachable from the source, including the source itself."""
        return [v for v in self._nodes.values() if self.reachable(v)]

    def unreachable_nodes(self) -> list:
        """Every node with no path from the source, in node iteration order."""
        return [v for v in self._nodes.values() if not self.reachable(v)]

    # --- paths ------------------------------------------------------------- #

    def predecessor_edge(self, node):
        """The edge used to reach `node`, or None for the source and unreachable
        nodes."""
        return self._predecessors[node.index]

    def path_to(self, node) -> list | None:
        """The edges from the source to `node`, in order, or None if unreachable.

        The source itself yields an empty list - a zero-length path exists and
        is distinct from no path at all, which is why unreachable is None rather
        than `[]`.
        """
        if not self.reachable(node):
            return None
        edges: list[Any] = []
        current = node
        # A shortest-path tree has no cycles, but bound the walk anyway so a
        # malformed predecessor array cannot hang the caller.
        for _ in range(len(self._nodes) + 1):
            if current.index == self.source.index:
                edges.reverse()
                return edges
            edge = self._predecessors[current.index]
            if edge is None:
                break
            edges.append(edge)
            current = self._other_end(edge, current)
        raise RuntimeError(
            "the predecessor array does not lead back to the source; the graph "
            "was probably modified after shortest_paths() was called"
        )

    def nodes_to(self, node) -> list | None:
        """The nodes from the source to `node`, in order, or None if unreachable.

        Includes both endpoints, so the source itself yields `[source]`.
        """
        edges = self.path_to(node)
        if edges is None:
            return None
        nodes = [self.source]
        current = self.source
        for edge in edges:
            current = self._other_end(edge, current)
            nodes.append(current)
        return nodes

    @staticmethod
    def _other_end(edge, node):
        """The endpoint of `edge` that is not `node`.

        Compared by index rather than by handle identity, since two Python
        wrappers can refer to the same underlying node.
        """
        return edge.source if edge.target.index == node.index else edge.target

    def __contains__(self, node) -> bool:
        return self.reachable(node)

    def __repr__(self) -> str:
        reached = sum(1 for v in self._nodes.values() if self.reachable(v))
        return (
            f"<ogdf.ShortestPaths from node {self.source.index} "
            f"algorithm={self.algorithm!r} reached={reached}/{len(self._nodes)}>"
        )


def shortest_paths(
    graph,
    source,
    weight=None,
    *,
    directed: bool = False,
    algorithm: str = "auto",
) -> ShortestPaths:
    """Single-source shortest paths, returning distances and the paths.

    `weight` is an `EdgeArrayDouble` (or `EdgeArrayInt` for Bellman-Ford); omit
    it to treat every edge as unit length, which makes this a BFS by another
    name.

    `algorithm` selects the engine:

    - `"auto"` (default) - Dijkstra, or Bellman-Ford if `weight` is an
      `EdgeArrayInt` containing a negative length.
    - `"dijkstra"` - exact, requires non-negative weights, honours `directed`.
    - `"bellman_ford"` - exact, admits negative lengths, requires an
      `EdgeArrayInt`, and always treats edges as directed. Raises
      `AlgorithmError` if a negative cycle is reachable, since no shortest path
      is then defined.

    >>> import ogdf
    >>> g, m = ogdf.from_edges([("a", "b"), ("b", "c")])
    >>> paths = ogdf.shortest_paths(g, m["a"])
    >>> paths.distance(m["c"]), len(paths.path_to(m["c"]))
    (2.0, 2)
    >>> paths.nodes_to(m["c"]) == [m["a"], m["b"], m["c"]]
    True
    """
    if algorithm not in ("auto", "dijkstra", "bellman_ford"):
        raise ValueError(
            f"unknown algorithm {algorithm!r}; "
            "expected 'auto', 'dijkstra', or 'bellman_ford'"
        )

    integral = isinstance(weight, _core.EdgeArrayInt)
    if algorithm == "auto":
        negative = integral and any(weight[e] < 0 for e in graph.edges())
        algorithm = "bellman_ford" if negative else "dijkstra"

    if algorithm == "bellman_ford":
        if weight is None:
            weight = _core.EdgeArrayInt(graph, 1)
        elif not integral:
            raise _core.PreconditionError(
                "shortest_paths(algorithm='bellman_ford') needs an EdgeArrayInt; "
                "OGDF's Bellman-Ford is defined over integer lengths. Use "
                "algorithm='dijkstra' for float weights (non-negative only)."
            )
        ok, distances, predecessors = _core.bellman_ford_tree(graph, source, weight)
        if not ok:
            raise _core.AlgorithmError(
                "shortest_paths: the graph contains a negative cycle reachable "
                "from the source, so no shortest path is defined"
            )
        return ShortestPaths(
            graph, source, distances, predecessors, "bellman_ford", True
        )

    if weight is None:
        weight = _core.EdgeArrayDouble(graph, 1.0)
    elif integral:
        # Accept an int array for convenience rather than making the caller
        # rebuild it; Dijkstra needs doubles.
        as_double = _core.EdgeArrayDouble(graph, 0.0)
        for e in graph.edges():
            as_double[e] = float(weight[e])
        weight = as_double
    distances, predecessors = _core.dijkstra_tree(graph, weight, source, directed)
    return ShortestPaths(graph, source, distances, predecessors, "dijkstra", directed)


class STCut(NamedTuple):
    """A minimum s-t cut: its total weight and the edges crossing it."""

    #: Total weight of the cut edges. By max-flow min-cut duality this equals
    #: the maximum s-t flow when `directed` is True.
    value: float
    #: The edges crossing from the source side to the sink side.
    edges: list


def min_st_cut(graph, weight, source, sink, *, directed: bool = True) -> STCut:
    """Minimum s-t cut, returning the value and the cut edges.

    Requires non-negative weights. With `directed` (the default) the cut value
    equals the directed maximum flow from `source` to `sink`; set it False to
    treat edges as undirected.

    A minimum cut need not be unique - the diamond `s->a, s->b, a->t, b->t,
    a->b` at unit capacity has two of value 2 - and which one OGDF reports is
    not specified.

    !!! note "Why there is no node partition"
        OGDF's `MinSTCutMaxFlow` exposes a front and a back cut, but those are
        the extreme cuts nearest the source and nearest the sink: when the
        minimum cut is not unique they are different cuts, and neither is
        guaranteed to be the one whose edges are returned here. Reporting them
        as `source_side` / `sink_side` would describe no single cut. If you
        need the partition, derive it from the edges you get back - the source
        side is what remains reachable from `source` once they are removed.

    >>> import ogdf
    >>> g, m = ogdf.from_edges([("s", "a"), ("a", "t")])
    >>> cut = ogdf.min_st_cut(g, ogdf.EdgeArrayDouble(g, 1.0), m["s"], m["t"])
    >>> cut.value
    1.0
    >>> value, edges = cut          # still unpacks as a pair
    >>> len(edges)
    1
    """
    value, edges = _core.st_cut(graph, weight, source, sink, directed)
    return STCut(value, edges)
