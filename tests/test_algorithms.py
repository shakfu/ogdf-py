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


def test_min_st_cut_matches_max_flow():
    g = ogdf.Graph()
    s, a, t = g.new_node(), g.new_node(), g.new_node()
    e1 = g.new_edge(s, a)
    e2 = g.new_edge(a, t)
    e3 = g.new_edge(s, t)
    cap = ogdf.EdgeArrayDouble(g)
    cap[e1], cap[e2], cap[e3] = 3.0, 2.0, 5.0
    value, edges = ogdf.min_st_cut(g, cap, s, t)
    # Max-flow min-cut duality: the cut value equals the max flow (7).
    flow = ogdf.EdgeArrayDouble(g)
    assert value == ogdf.max_flow(g, cap, s, t, flow) == 7.0
    # The min cut severs a->t (2) and s->t (5); the cut-edge weights sum to it.
    assert sum(cap[e] for e in edges) == value
    assert {e.index for e in edges} == {e2.index, e3.index}


def test_min_st_cut_undirected():
    # Two parallel-in-series paths between s and t; undirected cut is 2.
    c, nodes = cycle(4)  # s - x - t - y - s
    weight = ogdf.EdgeArrayDouble(c, 1.0)
    value, edges = ogdf.min_st_cut(c, weight, nodes[0], nodes[2], directed=False)
    assert value == 2.0
    assert len(list(edges)) == 2


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


# --- cut vertices and bridges --- #
def test_cut_vertices_and_bridges_path():
    g, nodes = path(4)  # a-b-c-d
    cut = {v.index for v in ogdf.cut_vertices(g)}
    assert cut == {1, 2}  # the two middle nodes
    assert len(ogdf.bridges(g)) == 3  # every edge is a bridge


def test_no_cut_vertices_in_cycle():
    c, _ = cycle(4)
    assert len(ogdf.cut_vertices(c)) == 0
    assert len(ogdf.bridges(c)) == 0


# --- Bellman-Ford --- #
def test_bellman_ford_negative_edge():
    g = ogdf.Graph()
    a, b, c = g.new_node(), g.new_node(), g.new_node()
    e1 = g.new_edge(a, b)
    e2 = g.new_edge(b, c)
    e3 = g.new_edge(a, c)
    length = ogdf.EdgeArrayInt(g)
    length[e1], length[e2], length[e3] = 4, -2, 5
    dist = ogdf.NodeArrayInt(g)
    assert ogdf.bellman_ford(g, a, length, dist)  # no negative cycle
    assert dist[c] == 2  # a->b->c (4-2) beats a->c (5)


# --- maximum-weight matching --- #
def test_maximum_weight_matching():
    g = ogdf.Graph()
    m = [g.new_node() for _ in range(4)]
    e0 = g.new_edge(m[0], m[1])
    e1 = g.new_edge(m[2], m[3])
    e2 = g.new_edge(m[1], m[2])
    weight = ogdf.EdgeArrayDouble(g)
    weight[e0], weight[e1], weight[e2] = 3.0, 3.0, 5.0
    matching = ogdf.EdgeArrayBool(g)
    total = ogdf.maximum_weight_matching(g, weight, matching)
    # Two disjoint edges (3 + 3) beat the single heavy edge (5).
    assert total == 6.0
    assert matching[e0] and matching[e1] and not matching[e2]


# --- min-cost flow --- #
def test_min_cost_flow():
    g = ogdf.Graph()
    s, a, t = g.new_node(), g.new_node(), g.new_node()
    e1 = g.new_edge(s, a)
    e2 = g.new_edge(a, t)
    e3 = g.new_edge(s, t)
    lower = ogdf.EdgeArrayInt(g, 0)
    upper = ogdf.EdgeArrayInt(g)
    upper[e1], upper[e2], upper[e3] = 2, 2, 2
    cost = ogdf.EdgeArrayDouble(g)
    cost[e1], cost[e2], cost[e3] = 1.0, 1.0, 5.0
    supply = ogdf.NodeArrayInt(g)
    supply[s], supply[a], supply[t] = 2, 0, -2
    flow = ogdf.EdgeArrayInt(g)
    assert ogdf.min_cost_flow(g, lower, upper, cost, supply, flow)
    # Route the 2 units through a (cost 1+1) rather than direct (cost 5).
    assert flow[e1] == 2 and flow[e2] == 2 and flow[e3] == 0


# --- Steiner tree --- #
def test_steiner_tree_path():
    g, nodes = path(4)  # a-b-c-d
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    total, edges = ogdf.steiner_tree(g, weight, [nodes[0], nodes[3]])
    # Connecting the two ends requires the whole path.
    assert total == 3.0
    assert len(edges) == 3


def test_steiner_tree_star():
    g = ogdf.Graph()
    center = g.new_node()
    leaves = [g.new_node() for _ in range(4)]
    for leaf in leaves:
        g.new_edge(center, leaf)
    weight = ogdf.EdgeArrayDouble(g, 2.0)
    total, edges = ogdf.steiner_tree(g, weight, leaves)
    # All four spokes are needed to connect the leaves.
    assert total == 8.0
    assert len(edges) == 4


# --- maximal planar subgraph --- #
def test_maximal_planar_subgraph_of_k5():
    k5 = ogdf.Graph()
    ogdf.complete_graph(k5, 5)  # non-planar; needs exactly one edge removed
    removed = ogdf.maximal_planar_subgraph(k5)
    assert len(removed) == 1  # 10 - 1 = 9 = 3*5 - 6 (maximal planar)

    # Rebuild the subgraph without the removed edges and confirm it is planar.
    removed_idx = {e.index for e in removed}
    sub = ogdf.Graph()
    nodes = [sub.new_node() for _ in range(k5.number_of_nodes())]
    for e in k5.edges():
        if e.index not in removed_idx:
            sub.new_edge(nodes[e.source.index], nodes[e.target.index])
    assert ogdf.is_planar(sub)


def test_maximal_planar_subgraph_already_planar():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 12, 18)
    assert len(ogdf.maximal_planar_subgraph(g)) == 0


# --- triconnectivity / SPQR --- #
def test_separation_pair():
    c, _ = cycle(6)  # biconnected, not triconnected
    sp = ogdf.separation_pair(c)
    assert sp is not None
    assert sp[0].index != sp[1].index

    k4 = ogdf.Graph()
    ogdf.complete_graph(k4, 4)  # triconnected -> no separation pair
    assert ogdf.separation_pair(k4) is None


def test_spqr_tree_summary():
    c, _ = cycle(6)  # a cycle is a single series (S) node
    assert ogdf.spqr_tree_summary(c) == {"S": 1, "P": 0, "R": 0, "nodes": 1}

    k4 = ogdf.Graph()
    ogdf.complete_graph(k4, 4)  # triconnected -> a single rigid (R) node
    assert ogdf.spqr_tree_summary(k4)["R"] == 1


def test_spqr_requires_biconnected():
    g, _ = path(4)  # not biconnected
    with pytest.raises(ValueError):
        ogdf.spqr_tree_summary(g)


# --- optional predicates --- #
def test_is_two_edge_connected():
    assert ogdf.is_two_edge_connected(cycle(4)[0])  # bridgeless
    assert not ogdf.is_two_edge_connected(path(4)[0])  # every edge a bridge


def test_is_regular():
    c, _ = cycle(5)  # every node has degree 2
    assert ogdf.is_regular(c)
    assert ogdf.is_regular(c, 2)
    assert not ogdf.is_regular(c, 3)


def test_is_arborescence():
    g = ogdf.Graph()
    root = g.new_node()
    for _ in range(3):
        g.new_edge(root, g.new_node())  # directed rooted tree
    assert ogdf.is_arborescence(g)
    assert not ogdf.is_arborescence(cycle(4)[0])


def test_triangulate():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 10, 15)
    ogdf.planar_embed(g)
    ogdf.triangulate(g)
    assert g.number_of_edges() == 3 * 10 - 6  # maximal planar
    assert ogdf.is_planar(g)


def test_bfs_distances():
    g, nodes = path(5)
    dist = ogdf.NodeArrayInt(g)
    ogdf.bfs_distances(g, nodes[0], dist)
    assert [dist[v] for v in nodes] == [0, 1, 2, 3, 4]


# --- A* search --- #
def test_a_star_search_path():
    g, nodes = path(5)  # a-b-c-d-e
    cost = ogdf.EdgeArrayDouble(g, 2.0)
    length, edges = ogdf.a_star_search(g, cost, nodes[0], nodes[4])
    assert length == 8.0  # 4 hops * 2.0
    edges = list(edges)
    assert len(edges) == 4
    # The returned edges form a walk from source to target.
    assert edges[0].source.index == nodes[0].index
    assert edges[-1].target.index == nodes[4].index


def test_a_star_search_unreachable():
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()  # no edge between them
    assert ogdf.a_star_search(g, ogdf.EdgeArrayDouble(g, 1.0), a, b) is None


def test_a_star_search_admissible_heuristic_is_optimal():
    # A shortcut edge must win even with a (zero) heuristic supplied. An
    # admissible heuristic never changes the optimal length.
    g = ogdf.Graph()
    n = [g.new_node() for _ in range(4)]
    e_long = [g.new_edge(n[i], n[i + 1]) for i in range(3)]  # 0-1-2-3
    e_short = g.new_edge(n[0], n[3])  # direct shortcut
    cost = ogdf.EdgeArrayDouble(g)
    for e in e_long:
        cost[e] = 1.0
    cost[e_short] = 2.0  # 2.0 < 3.0 for the long path
    length, edges = ogdf.a_star_search(g, cost, n[0], n[3], False, lambda v: 0.0)
    assert length == 2.0
    assert [e.index for e in edges] == [e_short.index]


# --- crossing number --- #
def test_crossing_number_planar_is_zero():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 15, 25)
    assert ogdf.crossing_number(g) == 0


def test_crossing_number_k5():
    k5 = ogdf.Graph()
    ogdf.complete_graph(k5, 5)  # crossing number of K5 is 1
    assert ogdf.crossing_number(k5) == 1
    assert k5.number_of_edges() == 10  # graph is not modified


def test_crossing_number_k6_at_least_three():
    k6 = ogdf.Graph()
    ogdf.complete_graph(k6, 6)  # true crossing number is 3
    # The planarizer yields a real drawing, so its count is >= the optimum.
    assert ogdf.crossing_number(k6) >= 3


def test_crossing_number_rejects_bad_permutations():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    with pytest.raises(ValueError):
        ogdf.crossing_number(g, 0)


# --- edge insertion (routing with crossings) --- #
def test_insert_edges_k5_single_crossing():
    k5 = ogdf.Graph()
    ogdf.complete_graph(k5, 5)
    # Removing any single edge leaves a maximal planar graph; reinserting it
    # forces exactly one crossing.
    e = list(k5.edges())[0]
    routes = ogdf.insert_edges(k5, [e])
    assert len(routes) == 1
    inserted, crossed = routes[0]
    assert inserted.index == e.index
    crossed = list(crossed)
    assert len(crossed) == 1
    # A valid drawing only crosses independent edges (no shared endpoint), and
    # never the inserted edge itself.
    endpoints = {e.source.index, e.target.index}
    other = crossed[0]
    assert other.index != e.index
    assert endpoints.isdisjoint({other.source.index, other.target.index})
    assert k5.number_of_edges() == 10  # graph unmodified


def test_insert_edges_matches_crossing_number_small():
    for n in (5, 6):
        g = ogdf.Graph()
        ogdf.complete_graph(g, n)
        removed = list(ogdf.maximal_planar_subgraph(g))
        routes = ogdf.insert_edges(g, removed)
        total = sum(len(list(c)) for _, c in routes)
        # Insertion into the fixed planar subgraph is an upper bound on the
        # crossing number; for these small complete graphs it is tight.
        assert total == ogdf.crossing_number(g)
        assert {ins.index for ins, _ in routes} == {e.index for e in removed}


def test_insert_edges_planar_no_crossings():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 12, 20)
    e = list(g.edges())[0]
    routes = ogdf.insert_edges(g, [e])
    # Removing and reinserting one edge of a planar graph needs no crossings.
    assert [len(list(c)) for _, c in routes] == [0]


def test_insert_edges_empty():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    assert list(ogdf.insert_edges(g, [])) == []


def test_insert_edges_rejects_non_planar_remainder():
    k6 = ogdf.Graph()
    ogdf.complete_graph(k6, 6)
    # K6 minus a single edge is still non-planar, so the remainder is invalid.
    with pytest.raises(ValueError):
        ogdf.insert_edges(k6, [list(k6.edges())[0]])


# --- k-connectivity --- #
def test_global_connectivity_known_values():
    c, _ = cycle(5)  # a cycle is 2-node- and 2-edge-connected
    assert ogdf.node_connectivity(c) == 2
    assert ogdf.edge_connectivity(c) == 2

    p, _ = path(4)  # a path is 1-connected
    assert ogdf.node_connectivity(p) == 1
    assert ogdf.edge_connectivity(p) == 1

    k4 = ogdf.Graph()
    ogdf.complete_graph(k4, 4)  # K4 is 3-connected
    assert ogdf.node_connectivity(k4) == 3
    assert ogdf.edge_connectivity(k4) == 3


def test_connectivity_trivial_graph_is_zero():
    g = ogdf.Graph()
    g.new_node()  # a single node
    assert ogdf.node_connectivity(g) == 0
    assert ogdf.edge_connectivity(g) == 0


def test_local_connectivity_menger():
    # Two internally disjoint s-t paths -> local connectivity 2.
    g = ogdf.Graph()
    s, t = g.new_node(), g.new_node()
    mids = [g.new_node() for _ in range(2)]
    for m in mids:
        g.new_edge(s, m)
        g.new_edge(m, t)
    assert ogdf.node_connectivity(g, s, t) == 2
    assert ogdf.edge_connectivity(g, s, t) == 2


def test_local_connectivity_rejects_same_node():
    g, nodes = path(3)
    with pytest.raises(ValueError):
        ogdf.node_connectivity(g, nodes[0], nodes[0])
