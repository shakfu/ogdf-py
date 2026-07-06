"""Tests for the graph generators."""

import ogdf


def test_complete_graph():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    assert g.number_of_nodes() == 5
    assert g.number_of_edges() == 10  # n*(n-1)/2
    assert ogdf.is_connected(g)


def test_complete_bipartite_graph():
    g = ogdf.Graph()
    ogdf.complete_bipartite_graph(g, 3, 4)
    assert g.number_of_nodes() == 7
    assert g.number_of_edges() == 12  # n*m
    assert ogdf.is_bipartite(g)


def test_wheel_graph():
    g = ogdf.Graph()
    ogdf.wheel_graph(g, 6)
    assert g.number_of_nodes() == 7  # rim + hub
    assert g.number_of_edges() == 12  # 6 rim + 6 spokes


def test_petersen_graph():
    g = ogdf.Graph()
    ogdf.petersen_graph(g)
    assert g.number_of_nodes() == 10
    assert g.number_of_edges() == 15
    assert not ogdf.is_planar(g)  # the Petersen graph is non-planar


def test_grid_graph():
    g = ogdf.Graph()
    ogdf.grid_graph(g, 3, 4)
    assert g.number_of_nodes() == 12
    assert ogdf.is_connected(g)
    assert ogdf.is_planar(g)


def test_cube_graph():
    g = ogdf.Graph()
    ogdf.cube_graph(g, 3)  # 3-cube -> 8 nodes, 12 edges
    assert g.number_of_nodes() == 8
    assert g.number_of_edges() == 12


def test_random_tree():
    g = ogdf.Graph()
    ogdf.random_tree(g, 20)
    assert g.number_of_nodes() == 20
    assert g.number_of_edges() == 19  # a tree has n-1 edges
    assert ogdf.is_tree(g)


def test_random_regular_graph():
    g = ogdf.Graph()
    ogdf.random_regular_graph(g, 10, 3)  # needs n*d even
    assert g.number_of_nodes() == 10


def test_regular_tree():
    g = ogdf.Graph()
    ogdf.regular_tree(g, 7, 2)  # 7 nodes, binary
    assert g.number_of_nodes() == 7
    assert ogdf.is_tree(g)


# --- additional deterministic generators --- #
def test_circulant_graph():
    g = ogdf.Graph()
    ogdf.circulant_graph(g, 8, [1, 2])  # each node joined to +-1, +-2 -> deg 4
    assert g.number_of_nodes() == 8
    assert g.number_of_edges() == 16  # 8 * 4 / 2


def test_complete_kpartite_graph():
    g = ogdf.Graph()
    ogdf.complete_kpartite_graph(g, [2, 3])  # == K(2,3)
    assert g.number_of_nodes() == 5
    assert g.number_of_edges() == 6
    assert ogdf.is_bipartite(g)


def test_suspension():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 3)  # triangle
    ogdf.suspension(g, 2)  # add 2 nodes, each joined to all 3
    assert g.number_of_nodes() == 5
    assert g.number_of_edges() == 9  # 3 + 2*3


# --- operations --- #
def test_graph_union():
    g1 = ogdf.Graph()
    ogdf.complete_graph(g1, 3)
    g2 = ogdf.Graph()
    ogdf.complete_graph(g2, 4)
    ogdf.graph_union(g1, g2)
    assert g1.number_of_nodes() == 7
    assert g1.number_of_edges() == 9  # 3 + 6


def test_complement():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(4)]
    for i in range(4):
        g.new_edge(nodes[i], nodes[(i + 1) % 4])  # C4: 4 edges
    ogdf.complement(g)
    assert g.number_of_edges() == 2  # K4 has 6 edges; 6 - 4 = 2 diagonals


def test_cartesian_product():
    a = ogdf.Graph()
    ogdf.complete_graph(a, 2)  # a single edge
    b = ogdf.Graph()
    ogdf.complete_graph(b, 2)
    product = ogdf.Graph()
    ogdf.cartesian_product(a, b, product)
    # K2 x K2 is a 4-cycle.
    assert product.number_of_nodes() == 4
    assert product.number_of_edges() == 4


# --- random models (smoke: counts and basic invariants) --- #
def test_preferential_attachment_graph():
    g = ogdf.Graph()
    ogdf.preferential_attachment_graph(g, 30, 2)
    assert g.number_of_nodes() == 30
    assert ogdf.is_connected(g)


def test_watts_strogatz_graph():
    g = ogdf.Graph()
    ogdf.random_watts_strogatz_graph(g, 20, 4, 0.2)
    assert g.number_of_nodes() == 20


def test_random_planar_triconnected_graph():
    g = ogdf.Graph()
    ogdf.random_planar_triconnected_graph(g, 20, 30)
    assert g.number_of_nodes() == 20
    assert ogdf.is_planar(g)


def test_random_series_parallel_dag():
    g = ogdf.Graph()
    ogdf.random_series_parallel_dag(g, 20)
    assert ogdf.is_acyclic(g)
