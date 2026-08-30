"""Conversion between OGDF graphs and ordinary Python data.

OGDF's model is faithful but foreign: nodes and edges are opaque handles owned
by a `Graph`, and per-node/per-edge data lives in `NodeArray`/`EdgeArray`
objects registered with that graph. This module bridges that model to the data
Python users already have - edge lists, dictionaries, NumPy arrays, NetworkX
graphs - without giving up the native representation underneath.

Node identity policy
--------------------
Every conversion here is driven by *keys*: the label a caller uses for a node on
the Python side. `from_edges` and `from_networkx` return the graph together with
a `mapping` dict from key to `Node`, and the reverse conversions take the same
dict (or default to `node.index`). Keys may be any hashable object.

`node.index` is stable for as long as the node exists, but OGDF reuses indices
after deletion, so a mapping captured before a mutation must not be reused
afterwards - see the handle-lifetime rules in the documentation.
"""

from __future__ import annotations

from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

from ogdf import _core

__all__ = [
    "edge_array_to_dict",
    "edge_array_to_list",
    "edges_where",
    "fill_edge_array",
    "fill_node_array",
    "from_edges",
    "from_networkx",
    "node_array_to_dict",
    "node_array_to_list",
    "nodes_where",
    "to_edges",
    "to_networkx",
]


def _require_networkx():
    try:
        import networkx  # noqa: PLC0415
    except ImportError:  # pragma: no cover - depends on the environment
        raise ImportError(
            "networkx is required for from_networkx/to_networkx. "
            "It is an optional dependency: pip install networkx"
        ) from None
    return networkx


# --------------------------------------------------------------------------- #
# Edge lists                                                                   #
# --------------------------------------------------------------------------- #


def from_edges(
    edges: Iterable[Sequence[Hashable]],
    *,
    nodes: Iterable[Hashable] = (),
    graph: Any = None,
) -> tuple[Any, dict[Hashable, Any]]:
    """Build a `Graph` from an iterable of `(source, target)` pairs.

    Nodes are created on first mention, in the order they are encountered;
    `nodes` names additional nodes to create first (isolated nodes, or a
    specific node ordering). Each pair may carry extra entries - a weight, say -
    which are ignored here, so an edge list of `(u, v, w)` triples works
    unchanged.

    Edges are added in the given direction. Repeating a pair creates a parallel
    edge rather than being ignored, matching OGDF's multigraph model; deduplicate
    first if that is not what you want.

    Returns `(graph, mapping)`, where `mapping` maps each key to its `Node`.

    >>> import ogdf
    >>> g, mapping = ogdf.from_edges([("a", "b"), ("b", "c")])
    >>> g.number_of_nodes(), g.number_of_edges()
    (3, 2)
    >>> mapping["a"].degree
    1
    """
    g = _core.Graph() if graph is None else graph
    mapping: dict[Hashable, Any] = {}

    def node_for(key: Hashable):
        v = mapping.get(key)
        if v is None:
            v = mapping[key] = g.new_node()
        return v

    for key in nodes:
        node_for(key)
    for pair in edges:
        items = tuple(pair)
        if len(items) < 2:
            raise ValueError(
                f"each edge needs at least a source and a target, got {items!r}"
            )
        g.new_edge(node_for(items[0]), node_for(items[1]))
    return g, mapping


def to_edges(
    graph: Any, *, keys: Mapping[Any, Hashable] | None = None
) -> list[tuple[Hashable, Hashable]]:
    """Return the graph's edges as `(source, target)` pairs, in edge order.

    By default each endpoint is reported as its `node.index`. Pass `keys` - a
    `Node`-to-key mapping, i.e. the inverse of what `from_edges` returns - to
    report the caller's own labels instead.

    >>> import ogdf
    >>> g, mapping = ogdf.from_edges([("a", "b"), ("b", "c")])
    >>> ogdf.to_edges(g, keys={v: k for k, v in mapping.items()})
    [('a', 'b'), ('b', 'c')]
    """
    if keys is None:
        return [(e.source.index, e.target.index) for e in graph.edges()]
    return [(keys[e.source], keys[e.target]) for e in graph.edges()]


# --------------------------------------------------------------------------- #
# Arrays <-> Python containers                                                 #
# --------------------------------------------------------------------------- #


def node_array_to_dict(
    array: Any, graph: Any, *, keys: Mapping[Any, Hashable] | None = None
) -> dict[Hashable, Any]:
    """Read a `NodeArray` into a dict keyed by `node.index` (or by `keys`)."""
    if keys is None:
        return {v.index: array[v] for v in graph.nodes()}
    return {keys[v]: array[v] for v in graph.nodes()}


def edge_array_to_dict(
    array: Any, graph: Any, *, keys: Mapping[Any, Hashable] | None = None
) -> dict[Hashable, Any]:
    """Read an `EdgeArray` into a dict keyed by `edge.index` (or by `keys`)."""
    if keys is None:
        return {e.index: array[e] for e in graph.edges()}
    return {keys[e]: array[e] for e in graph.edges()}


def node_array_to_list(array: Any, graph: Any) -> list[Any]:
    """Read a `NodeArray` into a list in the graph's node iteration order.

    Position `i` corresponds to the `i`-th node of `graph.nodes()`, which is not
    the same as `node.index` once nodes have been deleted. Pair it with
    `list(graph.nodes())` if you need the correspondence explicitly.
    """
    return [array[v] for v in graph.nodes()]


def edge_array_to_list(array: Any, graph: Any) -> list[Any]:
    """Read an `EdgeArray` into a list in the graph's edge iteration order."""
    return [array[e] for e in graph.edges()]


def fill_node_array(
    array: Any,
    values: Mapping[Hashable, Any] | Iterable[Any],
    graph: Any,
    *,
    keys: Mapping[Any, Hashable] | None = None,
) -> Any:
    """Write Python values into an existing `NodeArray`; returns the array.

    `values` is either a mapping keyed the way `node_array_to_dict` reports
    (by `node.index`, or by `keys` if given) or a sequence in node iteration
    order. Nodes missing from a mapping keep the array's current value.

    >>> import ogdf
    >>> g, mapping = ogdf.from_edges([("a", "b")])
    >>> weights = ogdf.NodeArrayDouble(g, 0.0)
    >>> keys = {v: k for k, v in mapping.items()}
    >>> _ = ogdf.fill_node_array(weights, {"a": 1.5}, g, keys=keys)
    >>> weights[mapping["a"]]
    1.5
    """
    return _fill(array, values, graph.nodes(), keys, lambda v: v.index, "node")


def fill_edge_array(
    array: Any,
    values: Mapping[Hashable, Any] | Iterable[Any],
    graph: Any,
    *,
    keys: Mapping[Any, Hashable] | None = None,
) -> Any:
    """Write Python values into an existing `EdgeArray`; returns the array.

    The counterpart of `fill_node_array`, keyed by `edge.index` by default.
    """
    return _fill(array, values, graph.edges(), keys, lambda e: e.index, "edge")


def _fill(array, values, elements, keys, default_key, what):
    elements = list(elements)
    if isinstance(values, Mapping):
        key_of: Callable[[Any], Hashable] = (
            default_key if keys is None else keys.__getitem__
        )
        for element in elements:
            key = key_of(element)
            if key in values:
                array[element] = values[key]
        return array
    values = list(values)
    if len(values) != len(elements):
        raise ValueError(
            f"expected {len(elements)} values for {len(elements)} {what}s, "
            f"got {len(values)}"
        )
    for element, value in zip(elements, values):
        array[element] = value
    return array


# --------------------------------------------------------------------------- #
# Result helpers                                                               #
# --------------------------------------------------------------------------- #


def nodes_where(array: Any, graph: Any) -> list[Any]:
    """The nodes whose value in a boolean `NodeArray` is true, in node order."""
    return [v for v in graph.nodes() if array[v]]


def edges_where(array: Any, graph: Any) -> list[Any]:
    """The edges whose value in a boolean `EdgeArray` is true, in edge order.

    This is what turns the array-output convention into an ordinary Python
    result: a spanning tree, a matching, or a cut is a list of edges.

    >>> import ogdf
    >>> g = ogdf.Graph()
    >>> ogdf.complete_graph(g, 4)
    >>> weight = ogdf.EdgeArrayDouble(g, 1.0)
    >>> in_tree = ogdf.EdgeArrayBool(g)
    >>> _ = ogdf.min_spanning_tree(g, weight, in_tree)
    >>> len(ogdf.edges_where(in_tree, g))
    3
    """
    return [e for e in graph.edges() if array[e]]


# --------------------------------------------------------------------------- #
# NetworkX                                                                     #
# --------------------------------------------------------------------------- #

# GraphAttributes fields copied to and from NetworkX node attributes. Geometry
# is always available; the label needs the NODE_LABEL flag.
_NODE_GEOMETRY = (
    ("x", "x", "set_x"),
    ("y", "y", "set_y"),
    ("width", "width", "set_width"),
    ("height", "height", "set_height"),
)


def from_networkx(
    nx_graph: Any,
    *,
    graph_attributes: bool = False,
    label_attribute: str | None = None,
) -> tuple[Any, ...]:
    """Convert a NetworkX graph to an OGDF `Graph`.

    Handles all four NetworkX classes. A `DiGraph`/`MultiDiGraph` contributes
    one OGDF edge per directed edge; an undirected graph contributes one edge
    per undirected edge, oriented arbitrarily (OGDF stores every edge with a
    source and a target, and algorithms that ignore direction are marked as
    such). Multigraphs contribute one OGDF edge per parallel edge, so the edge
    count is preserved. Self-loops are preserved.

    NetworkX node and edge *attributes* are not carried over automatically -
    OGDF has no general attribute store - but node identity is: the returned
    mapping takes each NetworkX node to its `Node`, so any attribute can be
    transferred with `fill_node_array` / `fill_edge_array`.

    With `graph_attributes=True` the result also contains a `GraphAttributes`
    whose `directed` flag matches the input; pass `label_attribute` to copy a
    NetworkX node attribute (or `"__node__"` for the node object itself) into
    the node labels.

    Returns `(graph, mapping)`, or `(graph, attributes, mapping)` when
    `graph_attributes` is true.

    >>> import networkx as nx                          # doctest: +SKIP
    >>> import ogdf                                    # doctest: +SKIP
    >>> g, mapping = ogdf.from_networkx(nx.cycle_graph(5))   # doctest: +SKIP
    >>> g.number_of_nodes(), g.number_of_edges()       # doctest: +SKIP
    (5, 5)
    """
    _require_networkx()
    g = _core.Graph()
    mapping = {key: g.new_node() for key in nx_graph.nodes()}
    for source, target in nx_graph.edges():
        g.new_edge(mapping[source], mapping[target])

    if not graph_attributes:
        return g, mapping

    flags = _core.NODE_GRAPHICS | _core.EDGE_GRAPHICS
    if label_attribute is not None:
        flags |= _core.NODE_LABEL
    ga = _core.GraphAttributes(g, flags)
    ga.directed = bool(nx_graph.is_directed())
    if label_attribute is not None:
        for key, v in mapping.items():
            if label_attribute == "__node__":
                value: Any = key
            else:
                value = nx_graph.nodes[key].get(label_attribute, "")
            ga.set_node_label(v, str(value))
    return g, ga, mapping


def to_networkx(
    graph: Any,
    attributes: Any = None,
    *,
    keys: Mapping[Any, Hashable] | None = None,
    directed: bool | None = None,
    multigraph: bool | None = None,
) -> Any:
    """Convert an OGDF graph to a NetworkX graph.

    Nodes are named by `node.index`, or by `keys` if a `Node`-to-key mapping is
    given. The NetworkX class is chosen to be lossless by default: directed
    when `attributes.directed` is set (or when `directed=True` is passed), and a
    multigraph whenever the graph actually has parallel edges or self-loops, so
    the edge count always survives the round trip. Both choices can be forced.

    When `attributes` is given, each node gets `x`, `y`, `width` and `height`
    attributes from the layout, plus `label` if the `NODE_LABEL` flag is
    enabled - which is what makes a laid-out OGDF drawing plottable with
    NetworkX or matplotlib:

    >>> import ogdf                                          # doctest: +SKIP
    >>> ga = ogdf.GraphAttributes(g)                         # doctest: +SKIP
    >>> ogdf.FMMMLayout().call(ga)                           # doctest: +SKIP
    >>> h = ogdf.to_networkx(g, ga)                          # doctest: +SKIP
    >>> pos = {n: (d["x"], d["y"]) for n, d in h.nodes(data=True)}  # doctest: +SKIP
    """
    nx = _require_networkx()
    if directed is None:
        directed = bool(attributes.directed) if attributes is not None else False
    if multigraph is None:
        multigraph = not _core.is_simple_undirected(graph)

    cls = {
        (False, False): nx.Graph,
        (True, False): nx.DiGraph,
        (False, True): nx.MultiGraph,
        (True, True): nx.MultiGraph if not directed else nx.MultiDiGraph,
    }[(bool(directed), bool(multigraph))]
    out = cls()

    key_of: Callable[[Any], Hashable] = (
        (lambda v: v.index) if keys is None else keys.__getitem__
    )
    has_label = attributes is not None and attributes.has(_core.NODE_LABEL)
    for v in graph.nodes():
        data: dict[str, Any] = {}
        if attributes is not None:
            for name, getter, _ in _NODE_GEOMETRY:
                data[name] = getattr(attributes, getter)(v)
            if has_label:
                data["label"] = attributes.node_label(v)
        out.add_node(key_of(v), **data)
    for e in graph.edges():
        out.add_edge(key_of(e.source), key_of(e.target))
    return out
