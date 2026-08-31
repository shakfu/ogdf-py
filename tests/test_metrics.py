"""Drawing-quality metrics.

The tests pin metrics to drawings whose correct answer is known by hand, since
a metric that is merely self-consistent is worthless for comparing layouts.
"""

import math

import pytest

import ogdf


def _placed(coords, edges=()):
    """A graph with nodes at the given coordinates and zero-sized node boxes."""
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in coords]
    for i, j in edges:
        g.new_edge(nodes[i], nodes[j])
    ga = ogdf.GraphAttributes(g)
    for v, (x, y) in zip(nodes, coords):
        ga.set_x(v, float(x))
        ga.set_y(v, float(y))
        ga.set_width(v, 0.0)
        ga.set_height(v, 0.0)
    return g, ga, nodes


def _convex_polygon(n):
    """K_n with its nodes in convex position: exactly C(n,4) crossings."""
    g = ogdf.Graph()
    ogdf.complete_graph(g, n)
    ga = ogdf.GraphAttributes(g)
    for i, v in enumerate(g.nodes()):
        ga.set_x(v, 100.0 * math.cos(2 * math.pi * i / n))
        ga.set_y(v, 100.0 * math.sin(2 * math.pi * i / n))
        ga.set_width(v, 0.0)
        ga.set_height(v, 0.0)
    return g, ga


# --------------------------------------------------------------------------- #
# Crossings                                                                    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("n,expected", [(4, 1), (5, 5), (6, 15)])
def test_complete_graph_in_convex_position(n, expected):
    # Every 4-subset of points in convex position contributes exactly one
    # crossing, so K_n drawn on a circle has C(n,4) of them.
    _, ga = _convex_polygon(n)
    assert ogdf.count_crossings(ga) == expected


def test_axis_aligned_edges_are_not_skipped():
    """Regression: a horizontal and a vertical edge crossing at right angles.

    OGDF's DSegment::intersection(..., endpoints=false) tests the segment's
    bounding rectangle, which is degenerate for an axis-aligned segment - every
    point lies on its boundary, so all of its intersections were discarded.
    That silently reported zero crossings for orthogonal and grid layouts.
    """
    _, ga, _ = _placed([(-10, 0), (10, 0), (0, -10), (0, 10)], [(0, 1), (2, 3)])
    assert ogdf.count_crossings(ga) == 1


def test_edges_sharing_a_node_do_not_cross_there():
    _, ga, _ = _placed([(0, 0), (10, 0), (0, 10)], [(0, 1), (0, 2)])
    assert ogdf.count_crossings(ga) == 0


def test_disjoint_edges_do_not_cross():
    _, ga, _ = _placed([(0, 0), (1, 0), (0, 5), (1, 5)], [(0, 1), (2, 3)])
    assert ogdf.count_crossings(ga) == 0


def test_bends_are_respected():
    # Two edges whose straight lines miss each other, but whose drawn polylines
    # cross because one is routed through a bend.
    g, ga, nodes = _placed([(0, 0), (10, 0), (0, 10), (10, 10)], [(0, 1), (2, 3)])
    assert ogdf.count_crossings(ga) == 0
    detour = next(iter(g.edges()))
    ga.add_bend(detour, 5.0, 20.0)  # route the bottom edge up over the top one
    assert ogdf.count_crossings(ga) == 2


def test_planar_layout_of_a_planar_graph_has_no_crossings():
    g = ogdf.Graph()
    with ogdf.seeded(4):
        ogdf.random_planar_triconnected_graph(g, 20, 40)
    ga = ogdf.GraphAttributes(g)
    ogdf.PlanarStraightLayout().call(ga)
    assert ogdf.count_crossings(ga) == 0


def test_drawing_crossings_are_at_least_the_graph_crossing_number():
    # No drawing can do better than the graph's crossing number.
    g, ga = _convex_polygon(6)
    assert ogdf.count_crossings(ga) >= ogdf.crossing_number(g, permutations=4)


# --------------------------------------------------------------------------- #
# Geometry                                                                     #
# --------------------------------------------------------------------------- #


def test_edge_lengths_measure_the_polyline():
    g, ga, _ = _placed([(0, 0), (3, 4)], [(0, 1)])
    assert ogdf.edge_lengths(ga) == [5.0]
    e = next(iter(g.edges()))
    ga.add_bend(e, 0.0, 4.0)  # now an L: 4 up then 3 across
    assert ogdf.edge_lengths(ga) == [7.0]


def test_bounding_box_includes_node_boxes():
    g, ga, nodes = _placed([(0, 0), (10, 0)], [(0, 1)])
    assert ogdf.bounding_box(ga) == (0.0, 0.0, 10.0, 0.0)
    for v in nodes:
        ga.set_width(v, 4.0)
        ga.set_height(v, 2.0)
    assert ogdf.bounding_box(ga) == (-2.0, -1.0, 12.0, 1.0)


def test_bounding_box_of_an_empty_graph():
    ga = ogdf.GraphAttributes(ogdf.Graph())
    assert ogdf.bounding_box(ga) == (0.0, 0.0, 0.0, 0.0)


def test_node_overlaps_counts_pairs_and_area():
    g, ga, nodes = _placed([(0, 0), (5, 0)], [])
    for v in nodes:
        ga.set_width(v, 10.0)
        ga.set_height(v, 10.0)
    # Boxes span x in [-5,5] and [0,10]: they share a 5x10 region.
    pairs, area = ogdf.node_overlaps(ga)
    assert (pairs, area) == (1, 50.0)


def test_zero_sized_nodes_never_overlap():
    _, ga, _ = _placed([(0, 0), (0, 0)], [])
    assert ogdf.node_overlaps(ga) == (0, 0.0)


def test_min_angle_of_a_right_angle():
    # Two edges leaving the origin, one east and one north.
    _, ga, _ = _placed([(0, 0), (10, 0), (0, 10)], [(0, 1), (0, 2)])
    assert ogdf.min_angle(ga) == pytest.approx(math.pi / 2)


def test_min_angle_of_a_convex_polygon():
    # At each node of K5 on a circle, the tightest angle is 180/5 = 36 degrees.
    _, ga = _convex_polygon(5)
    assert math.degrees(ogdf.min_angle(ga)) == pytest.approx(36.0)


def test_min_angle_is_none_without_a_branching_node():
    _, ga, _ = _placed([(0, 0), (1, 0)], [(0, 1)])
    assert ogdf.min_angle(ga) is None


# --------------------------------------------------------------------------- #
# Stress                                                                       #
# --------------------------------------------------------------------------- #


def _path_on_a_line(n, spacing=1.0):
    g = ogdf.Graph()
    nodes = []
    for _ in range(n):
        v = g.new_node()
        if nodes:
            g.new_edge(nodes[-1], v)
        nodes.append(v)
    ga = ogdf.GraphAttributes(g)
    for i, v in enumerate(nodes):
        ga.set_x(v, i * spacing)
        ga.set_y(v, 0.0)
    return g, ga, nodes


def test_perfect_embedding_has_zero_stress():
    _, ga, _ = _path_on_a_line(8)
    assert ogdf.stress(ga) == pytest.approx(0.0, abs=1e-9)


def test_stress_is_scale_invariant_when_normalized():
    _, small, _ = _path_on_a_line(8, spacing=1.0)
    _, large, _ = _path_on_a_line(8, spacing=37.5)
    assert ogdf.stress(small) == pytest.approx(ogdf.stress(large), abs=1e-9)
    # Without normalization the scale dominates, which is why it is the default.
    assert ogdf.stress(large, normalize=False) > 1.0


def test_stress_is_translation_invariant():
    _, ga, nodes = _path_on_a_line(8)
    before = ogdf.stress(ga)
    for v in nodes:
        ga.set_x(v, ga.x(v) + 1000.0)
        ga.set_y(v, ga.y(v) - 500.0)
    assert ogdf.stress(ga) == pytest.approx(before, abs=1e-9)


def test_a_worse_drawing_has_higher_stress():
    _, good, nodes = _path_on_a_line(8)
    _, bad, bad_nodes = _path_on_a_line(8)
    for v in bad_nodes:  # collapse the path onto one point
        bad.set_x(v, 0.0)
        bad.set_y(v, 0.0)
    assert ogdf.stress(bad) > ogdf.stress(good)


def test_stress_skips_disconnected_pairs():
    # Two separate edges: pairs across the components have no hop distance and
    # must not be treated as infinitely far apart.
    _, ga, _ = _placed([(0, 0), (1, 0), (500, 500), (501, 500)], [(0, 1), (2, 3)])
    assert math.isfinite(ogdf.stress(ga))


def test_stress_of_a_trivial_graph_is_zero():
    ga = ogdf.GraphAttributes(ogdf.Graph())
    assert ogdf.stress(ga) == 0.0


# --------------------------------------------------------------------------- #
# Aggregation and comparison                                                   #
# --------------------------------------------------------------------------- #


def test_drawing_metrics_reports_every_key():
    _, ga = _convex_polygon(5)
    metrics = ogdf.drawing_metrics(ga)
    assert metrics["nodes"] == 5
    assert metrics["edges"] == 10
    assert metrics["crossings"] == 5
    assert metrics["edge_length_min"] <= metrics["edge_length_mean"]
    assert metrics["edge_length_mean"] <= metrics["edge_length_max"]
    assert metrics["area"] > 0.0
    assert metrics["aspect_ratio"] >= 1.0
    assert metrics["min_angle_degrees"] == pytest.approx(36.0)
    assert metrics["stress"] >= 0.0


def test_drawing_metrics_handles_a_degenerate_drawing():
    ga = ogdf.GraphAttributes(ogdf.Graph())
    metrics = ogdf.drawing_metrics(ga)
    assert metrics["nodes"] == 0
    assert metrics["aspect_ratio"] is None
    assert metrics["min_angle"] is None
    assert metrics["edge_length_cv"] is None


def test_edge_length_cv_is_zero_for_uniform_edges():
    # A square: four edges of equal length.
    _, ga, _ = _placed(
        [(0, 0), (10, 0), (10, 10), (0, 10)], [(0, 1), (1, 2), (2, 3), (3, 0)]
    )
    assert ogdf.drawing_metrics(ga)["edge_length_cv"] == pytest.approx(0.0)


def test_compare_layouts_ranks_and_reports_failures():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 6)  # not planar
    rows = ogdf.compare_layouts(
        g,
        {
            "circular": ogdf.CircularLayout,
            "fmmm": ogdf.FMMMLayout,
            "planar": ogdf.SchnyderLayout,
        },
        seed=1,
    )
    assert {r["layout"] for r in rows} == {"circular", "fmmm", "planar"}
    # A layout whose preconditions are unmet is reported, not raised, and sorts
    # last so it never wins the comparison.
    assert rows[-1]["layout"] == "planar"
    assert "planar" in rows[-1]["error"] or "requires" in rows[-1]["error"]
    # The rest are ranked by crossings, then stress.
    ok = [r for r in rows if "error" not in r]
    assert ok == sorted(ok, key=lambda r: (r["crossings"], r["stress"]))


def test_compare_layouts_seeding_makes_runs_repeatable():
    g = ogdf.Graph()
    with ogdf.seeded(2):
        ogdf.random_graph(g, 30, 60)
    first = ogdf.compare_layouts(g, {"fmmm": ogdf.FMMMLayout}, seed=7)
    second = ogdf.compare_layouts(g, {"fmmm": ogdf.FMMMLayout}, seed=7)
    assert first == second


def test_compare_layouts_accepts_configured_instances():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)

    def configured():
        layout = ogdf.FMMMLayout()
        layout.set_unit_edge_length(50.0)
        return layout

    rows = ogdf.compare_layouts(g, {"tuned": configured}, seed=1)
    assert rows[0]["layout"] == "tuned"
    assert rows[0]["edge_length_mean"] > 0.0
