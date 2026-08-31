"""The one-call `layout()` facade over the layout classes."""

import pytest

import ogdf


def _planar(n=30, m=50, seed=1):
    g = ogdf.Graph()
    with ogdf.seeded(seed):
        ogdf.random_planar_connected_graph(g, n, m)
    return g


def _laid_out(ga):
    """True if the layout actually moved something off the origin."""
    return any(ga.x(v) != 0.0 or ga.y(v) != 0.0 for v in ga.graph.nodes())


# --------------------------------------------------------------------------- #
# Selecting the algorithm                                                      #
# --------------------------------------------------------------------------- #


def test_class_is_the_primary_form():
    ga = ogdf.layout(_planar(), ogdf.CircularLayout)
    assert _laid_out(ga)


def test_default_algorithm_is_fmmm():
    g = _planar()
    assert _laid_out(ogdf.layout(g))


def test_string_names_resolve():
    g = _planar()
    for name in ("fmmm", "FMMMLayout", "fmmmlayout"):
        assert _laid_out(ogdf.layout(g, name))


def test_aliases_cover_the_awkward_class_names():
    g = _planar()
    for alias, expected in (
        ("stress", ogdf.StressMinimization),
        ("kamada_kawai", ogdf.SpringEmbedderKK),
        ("mds", ogdf.PivotMDS),
        ("planar", ogdf.PlanarStraightLayout),
    ):
        assert alias in ogdf.layout_names()
        assert _laid_out(ogdf.layout(g, alias))
        del expected


def test_layout_names_are_derived_not_hand_listed():
    names = ogdf.layout_names()
    # Every bound layout answers to its own class name, so a newly bound one is
    # reachable without editing a table.
    for cls_name in ogdf.about()["capability_names"]["layouts"]:
        assert cls_name in names


def test_a_configured_instance_is_accepted():
    configured = ogdf.FMMMLayout()
    configured.set_unit_edge_length(60.0)
    ga = ogdf.layout(_planar(), configured, seed=1)
    assert ogdf.drawing_metrics(ga)["edge_length_mean"] > 0.0


def test_unknown_name_lists_the_alternatives():
    with pytest.raises(ValueError, match="unknown layout"):
        ogdf.layout(_planar(), "nope")
    try:
        ogdf.layout(_planar(), "nope")
    except ValueError as exc:
        assert "FMMMLayout" in str(exc)


def test_a_non_layout_is_rejected():
    with pytest.raises(TypeError, match="must be a layout"):
        ogdf.layout(_planar(), 42)


# --------------------------------------------------------------------------- #
# Options                                                                      #
# --------------------------------------------------------------------------- #


def test_options_reach_the_setters():
    g = _planar()
    short = ogdf.layout(g, ogdf.FMMMLayout, unit_edge_length=5.0, seed=1)
    long = ogdf.layout(g, ogdf.FMMMLayout, unit_edge_length=80.0, seed=1)
    assert (
        ogdf.drawing_metrics(long)["edge_length_mean"]
        > ogdf.drawing_metrics(short)["edge_length_mean"]
    )


def test_unknown_option_reports_what_is_accepted():
    with pytest.raises(TypeError, match="no option 'bogus'"):
        ogdf.layout(_planar(), ogdf.FMMMLayout, bogus=1)
    try:
        ogdf.layout(_planar(), ogdf.FMMMLayout, bogus=1)
    except TypeError as exc:
        assert "unit_edge_length" in str(exc)


def test_unknown_option_on_an_optionless_layout():
    with pytest.raises(TypeError, match="no options"):
        ogdf.layout(_planar(), ogdf.SchnyderLayout, bogus=1)


# --------------------------------------------------------------------------- #
# Pipeline                                                                     #
# --------------------------------------------------------------------------- #


def test_seed_makes_a_stochastic_layout_reproducible():
    g = _planar()
    first = ogdf.layout(g, ogdf.FMMMLayout, seed=99)
    second = ogdf.layout(g, ogdf.FMMMLayout, seed=99)
    assert [(first.x(v), first.y(v)) for v in g.nodes()] == [
        (second.x(v), second.y(v)) for v in g.nodes()
    ]


def test_preconditions_are_checked_before_any_work():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)  # not planar
    with pytest.raises(ogdf.InvalidGraphError, match="planar"):
        ogdf.layout(g, ogdf.SchnyderLayout)


def test_validation_can_be_turned_off_but_the_layout_still_refuses():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    # The binding's own guard is not bypassed by validate=False.
    with pytest.raises(ogdf.InvalidGraphError):
        ogdf.layout(g, ogdf.SchnyderLayout, validate=False)


def test_fit_places_the_drawing_in_the_box():
    ga = ogdf.layout(_planar(), ogdf.CircularLayout, fit=(800.0, 600.0), margin=20.0)
    min_x, min_y, max_x, max_y = ogdf.bounding_box(ga)
    assert min_x >= 20.0 - 1e-6
    assert min_y >= 20.0 - 1e-6
    assert max_x <= 780.0 + 1e-6
    assert max_y <= 580.0 + 1e-6


def test_normalize_moves_the_corner_to_the_origin():
    ga = ogdf.layout(_planar(), ogdf.CircularLayout, normalize=True)
    min_x, min_y, _, _ = ogdf.bounding_box(ga)
    assert (min_x, min_y) == pytest.approx((0.0, 0.0))


def test_pack_separates_components():
    g = ogdf.Graph()
    with ogdf.seeded(3):
        ogdf.random_graph(g, 30, 20)  # sparse: several components
    piled = ogdf.layout(g, ogdf.CircularLayout, pack=False)
    packed = ogdf.layout(g, ogdf.CircularLayout, pack=True, separation=25.0)
    assert ogdf.node_overlaps(packed)[0] <= ogdf.node_overlaps(piled)[0]


def test_existing_attributes_are_reused_so_styling_survives():
    g = _planar()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(10, 20, 30))
    result = ogdf.layout(g, ogdf.CircularLayout, attributes=ga)
    assert result is ga
    assert ga.fill_color(next(iter(g.nodes()))).red == 10


def test_result_is_ready_to_draw():
    ga = ogdf.layout(_planar(), ogdf.CircularLayout, fit=(400.0, 400.0))
    assert ogdf.to_svg(ga).startswith("<?xml")


def test_facade_matches_the_explicit_sequence():
    g = _planar()
    explicit = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.set_seed(5)
    layout = ogdf.FMMMLayout()
    layout.set_unit_edge_length(30.0)
    layout.call(explicit)

    viaFacade = ogdf.layout(g, ogdf.FMMMLayout, unit_edge_length=30.0, seed=5)
    assert [(explicit.x(v), explicit.y(v)) for v in g.nodes()] == [
        (viaFacade.x(v), viaFacade.y(v)) for v in g.nodes()
    ]
