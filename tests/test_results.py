"""Result objects: shortest paths with the tree, and cuts with both partitions."""

import math

import pytest

import ogdf


def _diamond():
    """s -> a -> t and s -> b -> t, plus a cross edge a-b. All unit weight."""
    return ogdf.from_edges([("s", "a"), ("s", "b"), ("a", "t"), ("b", "t"), ("a", "b")])


# --------------------------------------------------------------------------- #
# Shortest paths                                                               #
# --------------------------------------------------------------------------- #


def test_unweighted_paths_are_hop_counts():
    g, m = ogdf.from_edges([("a", "b"), ("b", "c")])
    paths = ogdf.shortest_paths(g, m["a"])
    assert paths.distance(m["a"]) == 0.0
    assert paths.distance(m["c"]) == 2.0
    assert paths.nodes_to(m["c"]) == [m["a"], m["b"], m["c"]]
    assert len(paths.path_to(m["c"])) == 2


def test_path_prefers_the_cheaper_route():
    # a->b costs 1, b->c costs 1, a->c costs 5: the two-hop route wins.
    g, m = ogdf.from_edges([("a", "b"), ("b", "c"), ("a", "c")])
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    ogdf.fill_edge_array(weight, [1.0, 1.0, 5.0], g)
    paths = ogdf.shortest_paths(g, m["a"], weight)
    assert paths.distance(m["c"]) == 2.0
    assert paths.nodes_to(m["c"]) == [m["a"], m["b"], m["c"]]


def test_source_has_an_empty_path_not_a_missing_one():
    g, m = ogdf.from_edges([("a", "b")])
    paths = ogdf.shortest_paths(g, m["a"])
    assert paths.path_to(m["a"]) == []
    assert paths.nodes_to(m["a"]) == [m["a"]]
    assert paths.predecessor_edge(m["a"]) is None


def test_unreachable_is_infinity_and_none():
    g, m = ogdf.from_edges([("a", "b")], nodes=["island"])
    paths = ogdf.shortest_paths(g, m["a"])
    island = m["island"]
    assert math.isinf(paths.distance(island))
    assert paths.path_to(island) is None
    assert paths.nodes_to(island) is None
    assert not paths.reachable(island)
    assert island not in paths
    assert paths.unreachable_nodes() == [island]
    assert set(paths.reachable_nodes()) == {m["a"], m["b"]}


def test_directed_mode_respects_edge_direction():
    g, m = ogdf.from_edges([("a", "b")])
    assert ogdf.shortest_paths(g, m["b"], directed=False).reachable(m["a"])
    assert not ogdf.shortest_paths(g, m["b"], directed=True).reachable(m["a"])


def test_distances_dict_uses_the_documented_keys():
    g, m = ogdf.from_edges([("a", "b")])
    paths = ogdf.shortest_paths(g, m["a"])
    assert paths.distances() == {0: 0.0, 1: 1.0}
    keys = {v: k for k, v in m.items()}
    assert paths.distances(keys=keys) == {"a": 0.0, "b": 1.0}


def test_bellman_ford_handles_negative_lengths():
    # a->b (2), b->c (-1), a->c (5): the cheapest a->c route costs 1.
    g, m = ogdf.from_edges([("a", "b"), ("b", "c"), ("a", "c")])
    length = ogdf.EdgeArrayInt(g, 0)
    ogdf.fill_edge_array(length, [2, -1, 5], g)
    paths = ogdf.shortest_paths(g, m["a"], length)
    assert paths.algorithm == "bellman_ford"  # chosen automatically
    assert paths.distance(m["c"]) == 1.0
    assert paths.nodes_to(m["c"]) == [m["a"], m["b"], m["c"]]


def test_auto_picks_dijkstra_when_nothing_is_negative():
    g, m = ogdf.from_edges([("a", "b")])
    length = ogdf.EdgeArrayInt(g, 3)
    paths = ogdf.shortest_paths(g, m["a"], length)
    assert paths.algorithm == "dijkstra"
    assert paths.distance(m["b"]) == 3.0


def test_negative_cycle_raises_rather_than_returning_nonsense():
    g, m = ogdf.from_edges([("a", "b"), ("b", "a")])
    length = ogdf.EdgeArrayInt(g, -1)
    with pytest.raises(ogdf.AlgorithmError, match="negative cycle"):
        ogdf.shortest_paths(g, m["a"], length, algorithm="bellman_ford")


def test_bellman_ford_rejects_float_weights_with_an_explanation():
    g, m = ogdf.from_edges([("a", "b")])
    with pytest.raises(ogdf.PreconditionError, match="EdgeArrayInt"):
        ogdf.shortest_paths(
            g, m["a"], ogdf.EdgeArrayDouble(g, 1.0), algorithm="bellman_ford"
        )


def test_dijkstra_still_rejects_negative_weights():
    g, m = ogdf.from_edges([("a", "b")])
    length = ogdf.EdgeArrayInt(g, -1)
    with pytest.raises(ogdf.PreconditionError, match="non-negative"):
        ogdf.shortest_paths(g, m["a"], length, algorithm="dijkstra")


def test_unknown_algorithm_is_rejected():
    g, m = ogdf.from_edges([("a", "b")])
    with pytest.raises(ValueError, match="unknown algorithm"):
        ogdf.shortest_paths(g, m["a"], algorithm="floyd")


def test_shortest_paths_agrees_with_the_array_api():
    g = ogdf.Graph()
    with ogdf.seeded(3):
        ogdf.random_graph(g, 40, 90)
    source = next(iter(g.nodes()))
    weight = ogdf.EdgeArrayDouble(g, 1.0)

    distance = ogdf.NodeArrayDouble(g)
    ogdf.dijkstra(g, weight, source, distance)
    paths = ogdf.shortest_paths(g, source, weight)

    for v in g.nodes():
        if paths.reachable(v):
            assert paths.distance(v) == distance[v]


def test_reported_path_actually_costs_the_reported_distance():
    g = ogdf.Graph()
    with ogdf.seeded(11):
        ogdf.random_graph(g, 30, 60)
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    for i, e in enumerate(g.edges()):
        weight[e] = 1.0 + (i % 7)
    source = next(iter(g.nodes()))
    paths = ogdf.shortest_paths(g, source, weight)

    for v in g.nodes():
        path = paths.path_to(v)
        if path is None:
            continue
        assert sum(weight[e] for e in path) == pytest.approx(paths.distance(v))
        # And the node walk lines up with the edge walk.
        assert len(paths.nodes_to(v)) == len(path) + 1


def test_repr_is_informative():
    g, m = ogdf.from_edges([("a", "b")])
    text = repr(ogdf.shortest_paths(g, m["a"]))
    assert "ShortestPaths" in text and "dijkstra" in text


# --------------------------------------------------------------------------- #
# Minimum s-t cut                                                              #
# --------------------------------------------------------------------------- #


def test_cut_reports_value_and_edges():
    g, m = _diamond()
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    cut = ogdf.min_st_cut(g, weight, m["s"], m["t"])

    assert cut.value == 2.0
    assert len(cut.edges) == 2
    assert sum(weight[e] for e in cut.edges) == cut.value


def test_cut_value_matches_max_flow_by_duality():
    g = ogdf.Graph()
    with ogdf.seeded(5):
        ogdf.random_digraph(g, 25, 60)
    nodes = list(g.nodes())
    source, sink = nodes[0], nodes[-1]
    capacity = ogdf.EdgeArrayDouble(g, 1.0)

    flow = ogdf.EdgeArrayDouble(g)
    value = ogdf.max_flow(g, capacity, source, sink, flow)
    cut = ogdf.min_st_cut(g, capacity, source, sink, directed=True)
    assert cut.value == pytest.approx(value)


def test_cut_edges_really_separate_source_from_sink():
    """Removing the cut edges must disconnect the sink from the source.

    This is the property a caller actually relies on, and the one that lets
    them derive the node partition themselves if they need it.
    """
    for seed in (1, 2, 3):
        g = ogdf.Graph()
        with ogdf.seeded(seed):
            ogdf.random_graph(g, 25, 55)
        nodes = list(g.nodes())
        source, sink = nodes[0], nodes[-1]
        capacity = ogdf.EdgeArrayDouble(g, 1.0)
        cut = ogdf.min_st_cut(g, capacity, source, sink, directed=False)

        # Walk the graph from the source without using a cut edge.
        removed = {e.index for e in cut.edges}
        adjacency: dict[int, list] = {v.index: [] for v in g.nodes()}
        for e in g.edges():
            if e.index not in removed:
                adjacency[e.source.index].append(e.target.index)
                adjacency[e.target.index].append(e.source.index)
        seen = {source.index}
        stack = [source.index]
        while stack:
            for nxt in adjacency[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        assert sink.index not in seen


def test_cut_is_a_named_tuple_that_still_unpacks_as_a_pair():
    g, m = _diamond()
    cut = ogdf.min_st_cut(g, ogdf.EdgeArrayDouble(g, 1.0), m["s"], m["t"])
    value, edges = cut
    assert value == cut.value
    assert edges == cut.edges
    assert set(cut._asdict()) == {"value", "edges"}


def test_cut_still_validates_its_arguments():
    g, m = _diamond()
    with pytest.raises(ogdf.PreconditionError, match="distinct"):
        ogdf.min_st_cut(g, ogdf.EdgeArrayDouble(g, 1.0), m["s"], m["s"])
