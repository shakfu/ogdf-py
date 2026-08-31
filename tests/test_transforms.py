"""Coordinate transforms over a finished drawing."""

import pytest

import ogdf


def _two_nodes(x1=0.0, y1=0.0, x2=10.0, y2=0.0, size=0.0):
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()
    e = g.new_edge(a, b)
    ga = ogdf.GraphAttributes(g)
    for v, (x, y) in zip((a, b), ((x1, y1), (x2, y2))):
        ga.set_x(v, x)
        ga.set_y(v, y)
        ga.set_width(v, size)
        ga.set_height(v, size)
    return g, ga, a, b, e


# --------------------------------------------------------------------------- #
# Translate / center / normalize                                               #
# --------------------------------------------------------------------------- #


def test_translate_moves_everything():
    _, ga, a, b, _ = _two_nodes()
    ogdf.translate(ga, 5.0, -3.0)
    assert (ga.x(a), ga.y(a)) == (5.0, -3.0)
    assert (ga.x(b), ga.y(b)) == (15.0, -3.0)


def test_normalize_puts_the_corner_at_the_origin():
    _, ga, _, _, _ = _two_nodes(x1=-100.0, y1=-50.0, x2=-20.0, y2=30.0)
    ogdf.normalize(ga)
    min_x, min_y, _, _ = ogdf.bounding_box(ga)
    assert (min_x, min_y) == (0.0, 0.0)


def test_normalize_does_not_rescale():
    _, ga, _, _, _ = _two_nodes(x1=-100.0, x2=-20.0)
    before = ogdf.edge_lengths(ga)
    ogdf.normalize(ga)
    assert ogdf.edge_lengths(ga) == before


def test_center_centres_the_bounding_box():
    _, ga, _, _, _ = _two_nodes(x1=100.0, x2=140.0)
    ogdf.center(ga, 0.0, 0.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert (min_x + max_x) / 2 == pytest.approx(0.0)
    assert (min_y + max_y) / 2 == pytest.approx(0.0)


def test_center_accepts_a_target_point():
    _, ga, _, _, _ = _two_nodes()
    ogdf.center(ga, 50.0, -25.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert (min_x + max_x) / 2 == pytest.approx(50.0)
    assert (min_y + max_y) / 2 == pytest.approx(-25.0)


# --------------------------------------------------------------------------- #
# Scale                                                                        #
# --------------------------------------------------------------------------- #


def test_scale_about_origin():
    _, ga, a, b, _ = _two_nodes()
    ogdf.scale(ga, 2.0, about="origin")
    assert ga.x(b) == 20.0
    assert ga.x(a) == 0.0


def test_scale_about_center_keeps_the_centre_put():
    _, ga, _, _, _ = _two_nodes(x1=0.0, x2=10.0)
    ogdf.scale(ga, 3.0, about="center")
    min_x, _, max_x, _ = ogdf.bounding_box(ga)
    assert (min_x + max_x) / 2 == pytest.approx(5.0)
    assert max_x - min_x == pytest.approx(30.0)


def test_scale_about_an_explicit_point():
    _, ga, a, b, _ = _two_nodes()
    ogdf.scale(ga, 2.0, about=(10.0, 0.0))
    assert ga.x(a) == -10.0  # 10 + (0 - 10) * 2
    assert ga.x(b) == 10.0  # the anchor does not move


def test_scale_axes_independently():
    _, ga, _, b, _ = _two_nodes(x2=10.0, y2=10.0)
    ogdf.scale(ga, 2.0, 3.0, about="origin")
    assert (ga.x(b), ga.y(b)) == (20.0, 30.0)


def test_scale_leaves_node_sizes_alone_by_default():
    # The point of scaling up is usually to separate overlapping nodes, which
    # scaling the boxes too would not achieve.
    _, ga, a, _, _ = _two_nodes(size=8.0)
    ogdf.scale(ga, 4.0)
    assert ga.width(a) == 8.0


def test_scale_can_scale_node_sizes():
    _, ga, a, _, _ = _two_nodes(size=8.0)
    ogdf.scale(ga, 4.0, scale_node_sizes=True)
    assert ga.width(a) == 32.0


def test_scaling_up_separates_overlapping_nodes():
    _, ga, _, _, _ = _two_nodes(x1=0.0, x2=5.0, size=10.0)
    assert ogdf.node_overlaps(ga)[0] == 1
    ogdf.scale(ga, 5.0)
    assert ogdf.node_overlaps(ga)[0] == 0


def test_scale_rejects_an_unknown_anchor():
    _, ga, _, _, _ = _two_nodes()
    with pytest.raises(ValueError, match="about must be"):
        ogdf.scale(ga, 2.0, about="middle")


# --------------------------------------------------------------------------- #
# Bends travel with the drawing                                                #
# --------------------------------------------------------------------------- #


def test_transforms_move_edge_bends():
    """A routed drawing must not be torn apart by a transform.

    Bends carry most of the geometry of an orthogonal or planarization drawing,
    and they are only reachable from Python through add_bend/clear_bends - which
    is why the transforms live in C++.
    """
    _, ga, _, _, e = _two_nodes()
    ga.add_bend(e, 5.0, 5.0)
    length_before = ogdf.edge_lengths(ga)[0]

    ogdf.translate(ga, 100.0, 100.0)
    assert ogdf.edge_lengths(ga)[0] == pytest.approx(length_before)

    ogdf.scale(ga, 2.0, about="origin")
    assert ogdf.edge_lengths(ga)[0] == pytest.approx(2.0 * length_before)


def test_bounding_box_accounts_for_bends_after_transforms():
    _, ga, _, _, e = _two_nodes()
    ga.add_bend(e, 5.0, 40.0)
    ogdf.normalize(ga)
    min_x, min_y, _, max_y = ogdf.bounding_box(ga)
    assert (min_x, min_y) == (0.0, 0.0)
    assert max_y == pytest.approx(40.0)


# --------------------------------------------------------------------------- #
# Fit to box                                                                   #
# --------------------------------------------------------------------------- #


def _circular(n=6, node_size=0.0):
    g = ogdf.Graph()
    ogdf.complete_graph(g, n)
    ga = ogdf.GraphAttributes(g)
    ogdf.CircularLayout().call(ga)
    for v in g.nodes():
        ga.set_width(v, node_size)
        ga.set_height(v, node_size)
    return g, ga


def test_fit_to_box_fills_the_binding_axis():
    _, ga = _circular()
    ogdf.fit_to_box(ga, 800.0, 600.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    width, height = max_x - min_x, max_y - min_y
    assert width <= 800.0 + 1e-9
    assert height <= 600.0 + 1e-9
    # One dimension is filled exactly; the drawing is centred in the other.
    assert width == pytest.approx(800.0) or height == pytest.approx(600.0)


def test_fit_to_box_respects_the_margin():
    _, ga = _circular()
    ogdf.fit_to_box(ga, 400.0, 400.0, margin=25.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert min_x >= 25.0 - 1e-9
    assert min_y >= 25.0 - 1e-9
    assert max_x <= 375.0 + 1e-9
    assert max_y <= 375.0 + 1e-9


def test_fit_to_box_preserves_aspect_ratio():
    _, ga = _circular()
    before = ogdf.drawing_metrics(ga)["aspect_ratio"]
    ogdf.fit_to_box(ga, 1000.0, 200.0)
    assert ogdf.drawing_metrics(ga)["aspect_ratio"] == pytest.approx(before)


def test_fit_to_box_enlarges_a_small_drawing():
    _, ga, _, _, _ = _two_nodes(x2=1.0)
    factor = ogdf.fit_to_box(ga, 500.0, 500.0)
    assert factor > 1.0
    min_x, _, max_x, _ = ogdf.bounding_box(ga)
    assert max_x - min_x == pytest.approx(500.0)


def test_fit_to_box_with_fixed_node_sizes_still_fits_exactly():
    _, ga = _circular(node_size=40.0)
    factor = ogdf.fit_to_box(ga, 300.0, 300.0, scale_node_sizes=False)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert max_x - min_x <= 300.0 + 1e-6
    assert max_y - min_y <= 300.0 + 1e-6
    # The binding axis is filled to within the bisection's tolerance.
    assert max(max_x - min_x, max_y - min_y) == pytest.approx(300.0, abs=1e-3)
    # And the node boxes really did keep their size.
    assert all(ga.width(v) == 40.0 for v in ga.graph.nodes())
    assert factor > 0.0


def test_fit_to_box_returns_zero_when_nodes_alone_are_too_big():
    _, ga = _circular(node_size=500.0)
    assert ogdf.fit_to_box(ga, 100.0, 100.0, scale_node_sizes=False) == 0.0


def test_fit_to_box_can_pin_to_the_corner():
    _, ga = _circular()
    ogdf.fit_to_box(ga, 400.0, 400.0, margin=10.0, center_in_box=False)
    min_x, min_y, _, _ = ogdf.bounding_box(ga)
    assert (min_x, min_y) == pytest.approx((10.0, 10.0))


def test_fit_to_box_rejects_a_degenerate_target():
    _, ga = _circular()
    with pytest.raises(ogdf.PreconditionError, match="must be positive"):
        ogdf.fit_to_box(ga, 0.0, 100.0)
    with pytest.raises(ogdf.PreconditionError, match="no room"):
        ogdf.fit_to_box(ga, 100.0, 100.0, margin=60.0)


# --------------------------------------------------------------------------- #
# Component packing                                                            #
# --------------------------------------------------------------------------- #


def _piled_components(count=3):
    """Disconnected components all sitting on top of each other at the origin."""
    g = ogdf.Graph()
    ga = None
    pairs = []
    for _ in range(count):
        u, v = g.new_node(), g.new_node()
        g.new_edge(u, v)
        pairs.append((u, v))
    ga = ogdf.GraphAttributes(g)
    for u, v in pairs:
        for node, x in ((u, 0.0), (v, 30.0)):
            ga.set_x(node, x)
            ga.set_y(node, 0.0)
            ga.set_width(node, 10.0)
            ga.set_height(node, 10.0)
    return g, ga


def test_pack_components_separates_a_pile():
    g, ga = _piled_components(3)
    assert ogdf.node_overlaps(ga)[0] > 0
    assert ogdf.pack_components(ga, separation=15.0) == 3
    assert ogdf.node_overlaps(ga)[0] == 0


def test_pack_components_leaves_a_connected_graph_alone():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    ga = ogdf.GraphAttributes(g)
    ogdf.CircularLayout().call(ga)
    before = [(ga.x(v), ga.y(v)) for v in g.nodes()]
    assert ogdf.pack_components(ga) == 1
    assert [(ga.x(v), ga.y(v)) for v in g.nodes()] == before


def test_pack_components_preserves_each_component_internally():
    # Packing may move a component, but must not distort it.
    _, ga = _piled_components(3)
    before = sorted(round(x, 6) for x in ogdf.edge_lengths(ga))
    ogdf.pack_components(ga, separation=20.0)
    assert sorted(round(x, 6) for x in ogdf.edge_lengths(ga)) == before


def test_pack_components_on_an_empty_graph():
    ga = ogdf.GraphAttributes(ogdf.Graph())
    assert ogdf.pack_components(ga) == 0


def test_pack_components_validates_its_arguments():
    _, ga = _piled_components(2)
    with pytest.raises(ogdf.PreconditionError, match="separation"):
        ogdf.pack_components(ga, separation=-1.0)
    with pytest.raises(ogdf.PreconditionError, match="page_ratio"):
        ogdf.pack_components(ga, page_ratio=0.0)


def test_pack_then_fit_is_the_expected_pipeline():
    g = ogdf.Graph()
    with ogdf.seeded(3):
        ogdf.random_graph(g, 30, 25)  # sparse enough to be disconnected
    ga = ogdf.GraphAttributes(g)
    ogdf.FMMMLayout().call(ga)
    ogdf.pack_components(ga, separation=30.0)
    ogdf.fit_to_box(ga, 1000.0, 800.0, margin=20.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert min_x >= 20.0 - 1e-6
    assert min_y >= 20.0 - 1e-6
    assert max_x <= 980.0 + 1e-6
    assert max_y <= 780.0 + 1e-6
