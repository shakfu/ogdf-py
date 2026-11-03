"""Wrong or misleading results fixed after 0.6.0 (REVIEW.md P4-P7, P9, P10, C15,
C16), and postconditions of the graph mutators (T1)."""

import math

import pytest

import ogdf
from ogdf import InvalidGraphError, PreconditionError


def _k(n):
    g = ogdf.Graph()
    ogdf.complete_graph(g, n)
    return g


# --- P4: every layout class is a layout ----------------------------------- #


@pytest.mark.parametrize("name", ["SpringEmbedderKK", "StressMinimization", "PivotMDS"])
def test_layouts_not_named_layout_resolve_by_name(name):
    assert name in ogdf.layout_names()
    assert name in ogdf.about()["capability_names"]["layouts"]
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (2, 0)])
    ga = ogdf.layout(g, name, seed=1)
    assert ga.bounding_box_width() > 0


def test_every_layout_class_is_counted_as_a_layout():
    names = ogdf.about()["capability_names"]
    for name in names["types"]:
        assert not hasattr(getattr(ogdf, name), "call"), name


# --- P5: TreeLayout's precondition ---------------------------------------- #


def test_validate_accepts_an_undirected_forest_tree_layout_draws():
    # Not a rooted forest (node 1 has two parents), but undirected-acyclic.
    g, _ = ogdf.from_edges([(0, 1), (2, 1)])
    assert ogdf.validate("TreeLayout", g) == []
    ogdf.layout(g, ogdf.TreeLayout)


def test_validate_still_rejects_a_cycle_for_tree_layout():
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (2, 0)])
    assert ogdf.validate("TreeLayout", g) == ["a tree or forest"]


# --- P6: Bellman-Ford is directed only ------------------------------------ #


def _negative_dag():
    g, m = ogdf.from_edges([("a", "b"), ("c", "b")])
    length = ogdf.EdgeArrayInt(g, 0)
    ogdf.fill_edge_array(length, [1, -1], g)
    return g, m, length


def test_auto_bellman_ford_refuses_undirected_semantics():
    g, m, length = _negative_dag()
    with pytest.raises(PreconditionError, match="directed=True"):
        ogdf.shortest_paths(g, m["a"], length)


def test_auto_bellman_ford_with_directed_true():
    g, m, length = _negative_dag()
    paths = ogdf.shortest_paths(g, m["a"], length, directed=True)
    assert paths.algorithm == "bellman_ford"
    assert paths.distance(m["b"]) == 1.0
    assert paths.distance(m["c"]) == math.inf


# --- P7: provenance records the seed a layout used ------------------------ #


def test_layout_seed_is_recorded_in_provenance():
    g = _k(5)
    ogdf.set_seed(5)
    ogdf.layout(g, seed=9)
    assert ogdf.provenance()["seed"] == 9


def test_compare_layouts_seed_is_recorded_in_provenance():
    g = _k(5)
    ogdf.set_seed(5)
    ogdf.compare_layouts(g, {"fmmm": ogdf.FMMMLayout}, seed=3)
    assert ogdf.provenance()["seed"] == 3


# --- P9: partial key mappings --------------------------------------------- #


def test_fill_node_array_skips_nodes_missing_from_keys():
    g, m = ogdf.from_edges([("a", "b")])
    arr = ogdf.NodeArrayDouble(g, 7.0)
    ogdf.fill_node_array(arr, {"a": 1.0}, g, keys={m["a"]: "a"})
    assert (arr[m["a"]], arr[m["b"]]) == (1.0, 7.0)


# --- P10: fit_to_box sizes ------------------------------------------------ #


@pytest.mark.parametrize(
    "width, height, margin",
    [
        (math.nan, 100.0, 0.0),
        (math.inf, 100.0, 0.0),
        (100.0, -1.0, 0.0),
        (100.0, 100.0, math.nan),
    ],
)
def test_fit_to_box_rejects_non_finite_or_non_positive_sizes(width, height, margin):
    ga = ogdf.layout(_k(4), ogdf.CircularLayout)
    before = ogdf.bounding_box(ga)
    with pytest.raises(PreconditionError):
        ogdf.fit_to_box(ga, width, height, margin=margin)
    assert ogdf.bounding_box(ga) == before


# --- C15: separation_pair ------------------------------------------------- #


def test_separation_pair_rejects_a_graph_that_is_not_biconnected():
    g, _ = ogdf.from_edges([(0, 1), (1, 2)])
    with pytest.raises(InvalidGraphError, match="biconnected"):
        ogdf.separation_pair(g)


def test_separation_pair_of_a_cycle_and_of_k4():
    cycle, _ = ogdf.from_edges([(0, 1), (1, 2), (2, 3), (3, 0)])
    pair = ogdf.separation_pair(cycle)
    assert pair is not None and pair[0] != pair[1]
    assert ogdf.separation_pair(_k(4)) is None


# --- C16: OGDF's own exceptions ------------------------------------------- #


def test_ogdf_algorithm_failure_maps_to_algorithm_error():
    with pytest.raises(ogdf.AlgorithmError, match="algorithm failure"):
        ogdf._core._throw_for_test("algorithm")


def test_other_ogdf_exceptions_map_to_ogdf_error():
    with pytest.raises(ogdf.OGDFError):
        ogdf._core._throw_for_test("other")


def test_maximum_weight_matching_rejects_self_loops():
    g, _ = ogdf.from_edges([(0, 0), (0, 1)])
    with pytest.raises(InvalidGraphError, match="self-loops"):
        ogdf.maximum_weight_matching(
            g, ogdf.EdgeArrayDouble(g, 1.0), ogdf.EdgeArrayBool(g)
        )


# --- T1: mutator postconditions ------------------------------------------- #


def _forest():
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (3, 4), (5, 5)])
    g.new_node()  # isolated
    return g


def test_make_connected():
    g = _forest()
    edges = g.number_of_edges()
    ogdf.make_connected(g)
    assert ogdf.is_connected(g)
    assert g.number_of_edges() > edges


def test_make_biconnected():
    g = _forest()
    ogdf.make_biconnected(g)
    assert ogdf.is_biconnected(g)


def test_make_acyclic():
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (2, 0), (2, 3), (3, 2)])
    assert not ogdf.is_acyclic(g)
    ogdf.make_acyclic(g)
    assert ogdf.is_acyclic(g)
    assert g.number_of_nodes() == 4


@pytest.mark.parametrize(
    "build, expected",
    [
        (lambda: _k(4), True),
        (lambda: _k(5), True),
        (lambda: ogdf.from_edges([(i, (i + 1) % 6) for i in range(6)])[0], False),
        (lambda: ogdf.from_edges([(0, 1), (1, 2)])[0], False),
    ],
    ids=["K4", "K5", "C6", "path"],
)
def test_is_triconnected(build, expected):
    assert ogdf.is_triconnected(build()) is expected
