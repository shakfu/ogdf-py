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
