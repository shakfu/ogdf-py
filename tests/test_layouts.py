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


# --- Tier 1 layouts (each has a precondition) --- #
def test_radial_tree_layout():
    g = ogdf.Graph()
    ogdf.random_tree(g, 20)  # requires a tree
    ga = ogdf.GraphAttributes(g)
    ogdf.RadialTreeLayout().call(ga)
    assert ga.bounding_box_width() > 0


def test_linear_layout():
    g = connected_graph()
    ga = ogdf.GraphAttributes(g)
    ogdf.LinearLayout().call(ga)
    # An arc diagram places nodes along a line -> constant y.
    ys = {round(ga.y(v), 3) for v in g.nodes()}
    assert len(ys) == 1


def test_tutte_layout():
    g = ogdf.Graph()
    ogdf.cube_graph(g, 3)  # 3-connected planar
    nodes = list(g.nodes())
    ga = ogdf.GraphAttributes(g)
    ogdf.TutteLayout().call(ga)
    coords = {(round(ga.x(v), 3), round(ga.y(v), 3)) for v in nodes}
    assert len(coords) == len(nodes)


def _dag(n):
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(n)]
    for i in range(n - 1):
        g.new_edge(nodes[i], nodes[i + 1])
    g.new_edge(nodes[0], nodes[n - 1])
    return g


@pytest.mark.parametrize("layout_cls", [ogdf.DominanceLayout, ogdf.VisibilityLayout])
def test_upward_layouts(layout_cls):
    g = _dag(6)  # directed acyclic graph
    ga = ogdf.GraphAttributes(g)
    layout_cls().call(ga)
    assert ga.bounding_box_width() > 0
    assert ga.bounding_box_height() > 0


# --- Tier 2 layouts --- #
@pytest.mark.parametrize(
    "layout_cls",
    [ogdf.MultilevelLayout, ogdf.ModularMultilevelMixer, ogdf.BalloonLayout],
)
def test_tier2_layouts(layout_cls):
    g = connected_graph(25, 35)
    nodes = list(g.nodes())
    ga = ogdf.GraphAttributes(g)
    layout_cls().call(ga)
    coords = [(ga.x(v), ga.y(v)) for v in nodes]
    assert all(x == x and y == y for x, y in coords)  # no NaNs
    assert len({(round(x, 2), round(y, 2)) for x, y in coords}) > 1


def test_balloon_rejects_disconnected():
    g = ogdf.Graph()
    g.new_node()
    g.new_node()  # two isolated nodes -> disconnected
    ga = ogdf.GraphAttributes(g)
    with pytest.raises(ValueError):
        ogdf.BalloonLayout().call(ga)


# --- planar grid layouts (require a simple planar graph, >= 3 nodes) --- #
@pytest.mark.parametrize(
    "layout_cls",
    [
        ogdf.FPPLayout,
        ogdf.PlanarStraightLayout,
        ogdf.PlanarDrawLayout,
        ogdf.MixedModelLayout,
    ],
)
def test_planar_grid_layouts_no_crossings(layout_cls):
    g = connected_graph(12, 18)  # planar, connected, simple
    nodes = list(g.nodes())
    ga = ogdf.GraphAttributes(g)
    layout_cls().call(ga)
    coords = [(ga.x(v), ga.y(v)) for v in nodes]
    assert all(x == x and y == y for x, y in coords)  # no NaNs
    # A planar drawing places every node at a distinct point.
    assert len({(round(x, 3), round(y, 3)) for x, y in coords}) == len(nodes)
    assert ga.bounding_box_width() > 0


@pytest.mark.parametrize(
    "layout_cls",
    [
        ogdf.FPPLayout,
        ogdf.PlanarStraightLayout,
        ogdf.PlanarDrawLayout,
        ogdf.MixedModelLayout,
    ],
)
def test_planar_grid_layouts_reject_non_planar(layout_cls):
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)  # K5 is not planar
    ga = ogdf.GraphAttributes(g)
    with pytest.raises(ValueError):
        layout_cls().call(ga)


def test_planar_grid_layout_rejects_too_small():
    g = ogdf.Graph()
    g.new_edge(g.new_node(), g.new_node())  # 2 nodes -> below the minimum of 3
    ga = ogdf.GraphAttributes(g)
    with pytest.raises(ValueError):
        ogdf.FPPLayout().call(ga)


def test_planar_grid_layout_setters():
    g = connected_graph(10, 14)
    ga = ogdf.GraphAttributes(g)
    layout = ogdf.PlanarStraightLayout()
    layout.set_separation(30.0)
    layout.set_size_optimization(True)
    layout.set_base_ratio(0.5)
    layout.call(ga)
    assert ga.bounding_box_width() > 0
