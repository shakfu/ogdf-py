"""Tests for the additional layout algorithms."""

import pytest

import ogdf


def connected_graph(n=12, m=18):
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, n, m)
    return g


@pytest.mark.parametrize(
    "layout_cls",
    [
        ogdf.StressMinimization,
        ogdf.PivotMDS,
        ogdf.GEMLayout,
        ogdf.SpringEmbedderKK,
    ],
)
def test_layout_produces_valid_distinct_coordinates(layout_cls):
    g = connected_graph()
    nodes = list(g.nodes())
    ga = ogdf.GraphAttributes(g)
    layout_cls().call(ga)

    coords = [(ga.x(v), ga.y(v)) for v in nodes]
    # No NaNs.
    assert all(x == x and y == y for x, y in coords)
    # A non-degenerate drawing spreads nodes out.
    assert len({(round(x, 2), round(y, 2)) for x, y in coords}) > 1
    assert ga.bounding_box_width() > 0


def test_schnyder_planar_layout():
    # Schnyder requires a simple planar graph with >= 3 nodes.
    g = connected_graph(10, 15)
    nodes = list(g.nodes())
    ga = ogdf.GraphAttributes(g)
    ogdf.SchnyderLayout().call(ga)
    coords = {(round(ga.x(v), 3), round(ga.y(v), 3)) for v in nodes}
    assert len(coords) == len(nodes)  # planar grid -> all distinct


def test_gem_respects_user_layout():
    # If an initial layout exists, GEM should refine it, not overwrite blindly.
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(5)]
    for i in range(5):
        g.new_edge(nodes[i], nodes[(i + 1) % 5])
    ga = ogdf.GraphAttributes(g)
    for i, v in enumerate(nodes):
        ga.set_x(v, float(i * 100))
        ga.set_y(v, 0.0)
    ogdf.GEMLayout().call(ga)
    # Still a valid, non-collapsed layout.
    coords = {(round(ga.x(v), 2), round(ga.y(v), 2)) for v in nodes}
    assert len(coords) == len(nodes)


def test_layout_configuration_setters():
    g = connected_graph()
    ga = ogdf.GraphAttributes(g)
    layout = ogdf.StressMinimization()
    layout.set_iterations(50)
    layout.set_edge_costs(100.0)
    layout.call(ga)
    assert ga.bounding_box_width() > 0
