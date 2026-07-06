"""Tests for the core graph algorithm bindings."""

import pytest

import ogdf


def path(n):
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(n)]
    for i in range(n - 1):
        g.new_edge(nodes[i], nodes[i + 1])
    return g, nodes


def cycle(n):
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(n)]
    for i in range(n):
        g.new_edge(nodes[i], nodes[(i + 1) % n])
    return g, nodes


# --- connectivity / structure predicates --- #
def test_connectivity_predicates():
    g, _ = path(4)
    assert ogdf.is_connected(g)
    assert ogdf.is_tree(g)
    assert ogdf.is_forest(g)
    assert ogdf.is_acyclic_undirected(g)
    assert not ogdf.is_biconnected(g)

    c, _ = cycle(4)
    assert ogdf.is_biconnected(c)
    assert not ogdf.is_tree(c)


def test_planarity():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 4)
    assert ogdf.is_planar(g)  # K4 is planar

    k5 = ogdf.Graph()
    ogdf.complete_graph(k5, 5)
    assert not ogdf.is_planar(k5)  # K5 is not planar

    assert ogdf.planar_embed(g)
    assert not ogdf.planar_embed(k5)


def test_bipartite():
    even = cycle(6)[0]
    assert ogdf.is_bipartite(even)
    odd = cycle(5)[0]
    assert not ogdf.is_bipartite(odd)

    coloring = ogdf.NodeArrayBool(even)
    assert ogdf.is_bipartite(even, coloring)
    # Adjacent nodes must get different colors.
    for e in even.edges():
        assert coloring[e.source] != coloring[e.target]


# --- components --- #
def test_connected_components():
    g = ogdf.Graph()
    a = [g.new_node() for _ in range(4)]
    g.new_edge(a[0], a[1])
    g.new_edge(a[2], a[3])
    comp = ogdf.NodeArrayInt(g)
    assert ogdf.connected_components(g, comp) == 2
    assert comp[a[0]] == comp[a[1]]
    assert comp[a[2]] == comp[a[3]]
    assert comp[a[0]] != comp[a[2]]


def test_strong_components():
    # Directed cycle -> one strong component; a DAG path -> n components.
    c, _ = cycle(4)
    comp = ogdf.NodeArrayInt(c)
    assert ogdf.strong_components(c, comp) == 1

    g, nodes = path(4)
    comp2 = ogdf.NodeArrayInt(g)
    assert ogdf.strong_components(g, comp2) == 4


def test_topological_numbering():
    g, nodes = path(4)  # already a DAG (edges point forward)
    num = ogdf.NodeArrayInt(g)
    ogdf.topological_numbering(g, num)
    # A valid topological order: each edge goes from lower to higher number.
    for e in g.edges():
        assert num[e.source] < num[e.target]


# --- shortest paths --- #
def test_dijkstra():
    g, nodes = path(5)
    weight = ogdf.EdgeArrayDouble(g, 2.0)
    dist = ogdf.NodeArrayDouble(g)
    ogdf.dijkstra(g, weight, nodes[0], dist)
    assert [dist[v] for v in nodes] == [0.0, 2.0, 4.0, 6.0, 8.0]


# --- spanning tree --- #
def test_min_spanning_tree():
    g, nodes = path(4)
    weight = ogdf.EdgeArrayDouble(g)
    for i, e in enumerate(g.edges()):
        weight[e] = float(i + 1)  # 1, 2, 3
    in_tree = ogdf.EdgeArrayBool(g)
    # A tree's MST is itself: 1 + 2 + 3 = 6.
    assert ogdf.min_spanning_tree(g, weight, in_tree) == 6.0
    assert all(in_tree[e] for e in g.edges())


def test_make_minimum_spanning_tree():
    c, _ = cycle(4)
    weight = ogdf.EdgeArrayDouble(c)
    for i, e in enumerate(c.edges()):
        weight[e] = float(i + 1)  # 1,2,3,4 -> MST drops the heaviest (4)
    total = ogdf.make_minimum_spanning_tree(c, weight)
    assert total == 6.0  # 1 + 2 + 3
    assert c.number_of_edges() == 3  # graph reduced to the tree


# --- flow / cut --- #
def test_max_flow():
    g = ogdf.Graph()
    s, a, t = g.new_node(), g.new_node(), g.new_node()
    e1 = g.new_edge(s, a)
    e2 = g.new_edge(a, t)
    e3 = g.new_edge(s, t)
    cap = ogdf.EdgeArrayDouble(g)
    cap[e1], cap[e2], cap[e3] = 3.0, 2.0, 5.0
    flow = ogdf.EdgeArrayDouble(g)
    # min(3,2)=2 via a, plus 5 direct = 7.
    assert ogdf.max_flow(g, cap, s, t, flow) == 7.0


def test_min_cut():
    c, _ = cycle(5)
    weight = ogdf.EdgeArrayDouble(c, 1.0)
    # A cycle's global min cut severs exactly two edges.
    assert ogdf.min_cut(c, weight) == 2.0


# --- matching --- #
def test_maximal_matching():
    g, nodes = path(5)
    matching = ogdf.maximal_matching(g)
    edges = list(matching)
    # A maximal matching is a valid matching: no shared endpoints.
    endpoints = []
    for e in edges:
        endpoints += [e.source.index, e.target.index]
    assert len(endpoints) == len(set(endpoints))


def test_maximum_matching_bipartite():
    g = ogdf.Graph()
    ogdf.complete_bipartite_graph(g, 2, 3)  # K(2,3): max matching = 2
    matching = ogdf.EdgeArrayBool(g)
    assert ogdf.maximum_matching_bipartite(g, matching) == 2


def test_matching_raises_on_non_bipartite():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)  # K5 is not bipartite
    with pytest.raises(Exception):
        ogdf.maximum_matching_bipartite(g, ogdf.EdgeArrayBool(g))


# --- coloring --- #
def test_node_coloring():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)  # K5 needs 5 colors
    colors = ogdf.NodeArrayInt(g)
    assert ogdf.node_coloring(g, colors) == 5
    # A proper coloring: adjacent nodes differ.
    for e in g.edges():
        assert colors[e.source] != colors[e.target]


def test_coloring_bipartite_uses_two():
    g = cycle(6)[0]  # bipartite -> 2 colors
    colors = ogdf.NodeArrayInt(g)
    assert ogdf.node_coloring(g, colors) == 2
