"""Inputs that used to crash, hang, or return wrong results (REVIEW.md C1-C14, P1-P3).

Each test fed the extension input that broke an OGDF precondition. Before the
fix most of them segfaulted the interpreter, so a regression aborts the run.
"""

import gc
import math

import pytest

import ogdf
from ogdf import InvalidGraphError, PreconditionError


def _k(n):
    g = ogdf.Graph()
    ogdf.complete_graph(g, n)
    return g


# --- C1: GraphAttributes flags -------------------------------------------- #


@pytest.mark.parametrize(
    "call",
    [
        lambda ga, v, e: ga.set_node_label(v, "x"),
        lambda ga, v, e: ga.node_label(v),
        lambda ga, v, e: ga.set_edge_label(e, "x"),
        lambda ga, v, e: ga.set_fill_color(v, ogdf.Color(1, 2, 3)),
        lambda ga, v, e: ga.set_node_stroke_width(v, 2.0),
        lambda ga, v, e: ga.set_edge_stroke_color(e, ogdf.Color(1, 2, 3)),
        lambda ga, v, e: ga.set_arrow(e, ogdf.EdgeArrow.LAST),
    ],
)
def test_accessor_without_its_flag_raises(call):
    g = _k(3)
    ga = ogdf.GraphAttributes(g)  # NODE_GRAPHICS | EDGE_GRAPHICS only
    with pytest.raises(PreconditionError, match="attribute"):
        call(ga, next(g.nodes()), next(g.edges()))


def test_accessor_with_its_flag_works():
    g = _k(3)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    v = next(g.nodes())
    ga.set_node_label(v, "x")
    assert ga.node_label(v) == "x"


@pytest.mark.parametrize(
    "call",
    [
        lambda ga: ogdf.FMMMLayout().call(ga),
        lambda ga: ogdf.SugiyamaLayout().call(ga),
        lambda ga: ogdf.edge_lengths(ga),
        lambda ga: ogdf.stress(ga),
        lambda ga: ogdf.translate_drawing(ga, 1.0, 1.0),
        lambda ga: ogdf.to_svg(ga),
        lambda ga: ogdf.to_tikz(ga),
        lambda ga: ga.x(next(ga.graph.nodes())),
        lambda ga: ga.bounding_box_width(),
    ],
)
def test_graphics_consumers_require_graphics_flags(call):
    ga = ogdf.GraphAttributes(_k(4), 0)
    with pytest.raises(PreconditionError, match="GRAPHICS"):
        call(ga)


def test_generic_svg_write_requires_graphics_flags(tmp_path):
    ga = ogdf.GraphAttributes(_k(4), 0)
    with pytest.raises(PreconditionError):
        ogdf.write(ga, str(tmp_path / "a.svg"))


# --- C2 / C3: handle lifetime --------------------------------------------- #
#
# A handle whose element is gone is marked not ready, so nanobind refuses it
# with a TypeError and a RuntimeWarning before any C++ code runs.


def _rejected(use):
    with pytest.warns(RuntimeWarning, match="uninitialized instance"):
        with pytest.raises(TypeError):
            use()


def test_iterated_node_is_rejected_after_its_graph_is_destroyed():
    g = _k(50)
    n = list(g.nodes())[7]
    del g
    gc.collect()
    _rejected(lambda: n.degree)


def test_stale_handle_at_a_reused_address_names_the_new_element():
    # Wrong but memory-safe: the documented limit of address-based tracking.
    g = _k(50)
    n = list(g.nodes())[7]
    del g
    gc.collect()
    churn = [_k(50) for _ in range(20)]
    owners = [h for h in churn if n in set(h.nodes())]
    if not owners:
        pytest.skip("the allocator did not reuse the address")
    assert len(owners) == 1
    assert n.degree == 49


def test_returned_nodes_keep_their_graph_alive():
    g, _ = ogdf.from_edges([(0, 1), (1, 2)])
    cut = ogdf.cut_vertices(g)
    del g
    gc.collect()
    assert cut[0].degree == 2


def test_new_node_keeps_its_graph_alive():
    g = ogdf.Graph()
    v = g.new_node()
    g.new_edge(v, g.new_node())
    del g
    gc.collect()
    assert v.degree == 1


def test_handle_after_clear_is_rejected():
    g = _k(5)
    e = next(g.edges())
    v = next(g.nodes())
    g.clear()
    _rejected(lambda: e.source)
    _rejected(lambda: v.degree)
    _rejected(lambda: ogdf.NodeArrayInt(g)[v])


def test_stale_edge_is_not_confused_with_a_reused_node():
    # OGDF's pool can hand a freed edge's address to a new node.
    g = _k(5)
    edges = list(g.edges())
    ogdf.random_graph(g, 0, 0)
    keep = [_k(30) for _ in range(3)]
    for e in edges:
        _rejected(lambda: e.source)
    del keep


def test_handle_deleted_by_a_mutator_is_rejected_by_arrays():
    g = _k(5)
    edges = list(g.edges())
    ogdf.make_minimum_spanning_tree(g, ogdf.EdgeArrayDouble(g, 1.0))
    a = ogdf.EdgeArrayInt(g)
    live = set(g.edges())
    deleted = [e for e in edges if e not in live]
    assert len(deleted) == 6
    _rejected(lambda: a[deleted[0]])


def test_new_node_at_a_reused_address_is_usable():
    g = ogdf.Graph()
    stale = []
    for _ in range(100):
        stale.append(g.new_node())
        g.clear()
    v = g.new_node()
    assert v.degree == 0
    a = ogdf.NodeArrayInt(g, 3)
    assert a[v] == 3


# --- C4 / C18: handles and arrays from another graph ---------------------- #


def _foreign_node_array(size):
    h = ogdf.Graph()
    ogdf.empty_graph(h, size)
    return ogdf.NodeArrayInt(h)


@pytest.mark.parametrize(
    "call",
    [
        lambda g: ogdf.connected_components(g, _foreign_node_array(1)),
        lambda g: ogdf.strong_components(g, _foreign_node_array(1)),
        lambda g: ogdf.biconnected_components(g, ogdf.EdgeArrayInt(_k(2))),
        lambda g: ogdf.is_bipartite(g, ogdf.NodeArrayBool(_k(1))),
        lambda g: ogdf.bellman_ford(
            g, next(g.nodes()), ogdf.EdgeArrayInt(_k(2)), ogdf.NodeArrayInt(g)
        ),
    ],
)
def test_array_of_another_graph_is_rejected(call):
    g = ogdf.Graph()
    ogdf.random_graph(g, 200, 300)
    with pytest.raises(PreconditionError, match="different graph"):
        call(g)


def test_array_indexed_by_a_node_of_another_graph_raises():
    g = _k(1)
    a = ogdf.NodeArrayInt(g)
    h = ogdf.Graph()
    ogdf.empty_graph(h, 1000)
    with pytest.raises(PreconditionError, match="different graph"):
        a[list(h.nodes())[-1]] = 5


@pytest.mark.parametrize(
    "call",
    [
        lambda g, x: g.new_edge(next(g.nodes()), x),
        lambda g, x: ogdf.dijkstra(
            g, ogdf.EdgeArrayDouble(g, 1.0), x, ogdf.NodeArrayDouble(g)
        ),
        lambda g, x: ogdf.node_connectivity(g, next(g.nodes()), x),
        lambda g, x: ogdf.max_flow(
            g, ogdf.EdgeArrayDouble(g, 1.0), next(g.nodes()), x, ogdf.EdgeArrayDouble(g)
        ),
    ],
)
def test_node_argument_of_another_graph_is_rejected(call):
    g = _k(3)
    h = _k(30)  # must stay alive, or its handles are invalid rather than foreign
    other = list(h.nodes())[-1]
    with pytest.raises(PreconditionError, match="different graph"):
        call(g, other)


def test_reader_rejects_attributes_of_another_graph(tmp_path):
    path = str(tmp_path / "a.gml")
    g = _k(4)
    ogdf.write_gml(ogdf.GraphAttributes(g), path)
    h = ogdf.Graph()
    with pytest.raises(PreconditionError, match="different graph"):
        ogdf.read_gml(ogdf.GraphAttributes(h), g, path)


# --- C6: list arguments --------------------------------------------------- #


@pytest.mark.parametrize("bad", [None, 3, "a"])
def test_steiner_tree_rejects_non_node_terminals(bad):
    g = _k(4)
    with pytest.raises(TypeError, match="ogdf.Node"):
        ogdf.steiner_tree(g, ogdf.EdgeArrayDouble(g, 1.0), [bad, next(g.nodes())])


def test_steiner_tree_rejects_terminals_in_different_components():
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()
    with pytest.raises(InvalidGraphError, match="one connected component"):
        ogdf.steiner_tree(g, ogdf.EdgeArrayDouble(g, 1.0), [a, b])


def test_steiner_tree_rejects_foreign_terminals():
    g = _k(4)
    h = _k(40)
    other = list(h.nodes())[-1]
    with pytest.raises(PreconditionError, match="different graph"):
        ogdf.steiner_tree(g, ogdf.EdgeArrayDouble(g, 1.0), [other])


def test_insert_edges_rejects_bad_items():
    g = _k(5)
    with pytest.raises(TypeError, match="ogdf.Edge"):
        ogdf.insert_edges(g, [None])
    h = _k(30)
    with pytest.raises(PreconditionError, match="different graph"):
        ogdf.insert_edges(g, [list(h.edges())[-1]])


# --- C7 / P1: layouts that need a connected graph ------------------------- #

DISCONNECTED_CRASHERS = [
    "FPPLayout",
    "MixedModelLayout",
    "SchnyderLayout",
    "DominanceLayout",
    "VisibilityLayout",
]


@pytest.mark.parametrize("name", DISCONNECTED_CRASHERS)
def test_layout_rejects_disconnected_graph(name):
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (3, 4)])
    with pytest.raises(InvalidGraphError, match="connected"):
        getattr(ogdf, name)().call(ogdf.GraphAttributes(g))
    assert "connected" in ogdf.validate(name, g)


@pytest.mark.parametrize("name", ["PlanarStraightLayout", "PlanarDrawLayout"])
def test_planar_layouts_that_augment_still_accept_disconnected_graphs(name):
    g, _ = ogdf.from_edges([(0, 1), (1, 2), (3, 4)])
    getattr(ogdf, name)().call(ogdf.GraphAttributes(g))


# --- C8: spanning forest -------------------------------------------------- #


def test_min_spanning_tree_covers_every_component():
    g, _ = ogdf.from_edges([(0, 1), (2, 3), (3, 4), (2, 4)])
    w = ogdf.EdgeArrayDouble(g, 1.0)
    in_tree = ogdf.EdgeArrayBool(g)
    assert ogdf.min_spanning_tree(g, w, in_tree) == 3.0
    assert sum(in_tree[e] for e in g.edges()) == 3


def test_min_spanning_tree_of_an_empty_graph_is_empty():
    g = ogdf.Graph()
    assert (
        ogdf.min_spanning_tree(g, ogdf.EdgeArrayDouble(g), ogdf.EdgeArrayBool(g)) == 0.0
    )


def test_min_spanning_tree_picks_lightest_edges():
    g, m = ogdf.from_edges([(0, 1), (1, 2), (0, 2)])
    w = ogdf.EdgeArrayDouble(g)
    for e, cost in zip(g.edges(), (1.0, 5.0, 2.0)):
        w[e] = cost
    in_tree = ogdf.EdgeArrayBool(g)
    assert ogdf.min_spanning_tree(g, w, in_tree) == 3.0
    assert [in_tree[e] for e in g.edges()] == [True, False, True]


def test_min_spanning_tree_rejects_nan():
    g, _ = ogdf.from_edges([(0, 1)])
    with pytest.raises(PreconditionError, match="NaN"):
        ogdf.min_spanning_tree(
            g, ogdf.EdgeArrayDouble(g, math.nan), ogdf.EdgeArrayBool(g)
        )


# --- C9 ------------------------------------------------------------------- #


def test_planar_embed_planar_graph_leaves_non_planar_input_alone():
    g = _k(5)
    with pytest.raises(InvalidGraphError, match="planar"):
        ogdf.planar_embed_planar_graph(g)
    assert (g.number_of_nodes(), g.number_of_edges()) == (5, 10)


# --- C10: generators ------------------------------------------------------ #


@pytest.mark.parametrize(
    "call",
    [
        lambda g: ogdf.random_graph(g, -3, 5),
        lambda g: ogdf.random_graph(g, 0, 5),
        lambda g: ogdf.globe_graph(g, 0, 0),
        lambda g: ogdf.globe_graph(g, 3, 0),
        lambda g: ogdf.random_series_parallel_dag(g, 0),
        lambda g: ogdf.random_regular_graph(g, 4, 7),
        lambda g: ogdf.random_regular_graph(g, 5, 3),
        lambda g: ogdf.random_watts_strogatz_graph(g, 4, 10, 0.5),
        lambda g: ogdf.suspension(g, -1),
        lambda g: ogdf.cube_graph(g, 31),
        lambda g: ogdf.grid_graph(g, 0, 3, True, False),
        lambda g: ogdf.random_hierarchy(g, -1, 0, False, False, False),
        lambda g: ogdf.random_digraph(g, 5, 60),
        lambda g: ogdf.regular_lattice_graph(g, 6, 3),
        lambda g: ogdf.petersen_graph(g, 5, 3),
    ],
)
def test_generator_rejects_invalid_arguments(call):
    with pytest.raises(PreconditionError):
        call(ogdf.Graph())


def test_graph_operations_reject_aliased_arguments():
    g = _k(3)
    with pytest.raises(PreconditionError, match="different"):
        ogdf.graph_union(g, g)
    with pytest.raises(PreconditionError, match="different"):
        ogdf.cartesian_product(g, g, g)
    assert g.number_of_nodes() == 3


def test_cube_graph_at_its_limit_is_still_exact():
    g = ogdf.Graph()
    ogdf.cube_graph(g, 10)
    assert g.number_of_nodes() == 1024


# --- C11: min-cost flow --------------------------------------------------- #


def _flow_problem():
    g, m = ogdf.from_edges([(0, 1)])
    supply = ogdf.NodeArrayInt(g)
    supply[m[0]], supply[m[1]] = 3, -3
    return g, supply


def test_min_cost_flow_rejects_unbalanced_supply():
    g, supply = _flow_problem()
    supply[next(g.nodes())] = 4
    E = ogdf.EdgeArrayInt
    with pytest.raises(PreconditionError, match="sum to zero"):
        ogdf.min_cost_flow(g, E(g), E(g, 5), ogdf.EdgeArrayDouble(g, 1.0), supply, E(g))


def test_min_cost_flow_rejects_crossed_bounds():
    g, supply = _flow_problem()
    E = ogdf.EdgeArrayInt
    with pytest.raises(PreconditionError, match="lower_bound"):
        ogdf.min_cost_flow(
            g, E(g, 7), E(g, 5), ogdf.EdgeArrayDouble(g, 1.0), supply, E(g)
        )


def test_min_cost_flow_solves_a_feasible_problem():
    g, m = ogdf.from_edges([(0, 1), (1, 2)])
    supply = ogdf.NodeArrayInt(g)
    supply[m[0]], supply[m[2]] = 3, -3
    E = ogdf.EdgeArrayInt
    flow = E(g)
    assert ogdf.min_cost_flow(
        g, E(g), E(g, 5), ogdf.EdgeArrayDouble(g, 1.0), supply, flow
    )
    assert [flow[e] for e in g.edges()] == [3, 3]


def test_min_cost_flow_rejects_an_infeasible_solution_from_ogdf():
    # Reinelt returns True with zero flow on this one-edge network.
    g, supply = _flow_problem()
    E = ogdf.EdgeArrayInt
    with pytest.raises(ogdf.AlgorithmError, match="conservation"):
        ogdf.min_cost_flow(g, E(g), E(g, 5), ogdf.EdgeArrayDouble(g, 1.0), supply, E(g))


# --- C12: setters that made a later call hang or crash -------------------- #


@pytest.mark.parametrize("cost", [0.0, -1.0, math.nan, math.inf])
def test_pivot_mds_rejects_non_positive_edge_costs(cost):
    with pytest.raises(PreconditionError):
        ogdf.PivotMDS().set_edge_costs(cost)


def test_sugiyama_rejects_zero_runs():
    with pytest.raises(PreconditionError):
        ogdf.SugiyamaLayout().set_runs(0)


# --- C13: Bellman-Ford ---------------------------------------------------- #

UNREACHABLE = 2**31 - 1


def test_bellman_ford_does_not_relax_out_of_unreachable_nodes():
    # OGDF's version added 5 to INT_MAX at node 2, wrapping node 3 negative.
    g, m = ogdf.from_edges([(0, 1), (2, 3)])
    d = ogdf.NodeArrayInt(g)
    assert ogdf.bellman_ford(g, m[0], ogdf.EdgeArrayInt(g, 5), d)
    assert [d[m[k]] for k in range(4)] == [0, 5, UNREACHABLE, UNREACHABLE]


def test_bellman_ford_rejects_lengths_that_could_overflow():
    g, m = ogdf.from_edges([(0, 1), (1, 2)])
    with pytest.raises(PreconditionError, match="2\\*\\*31"):
        ogdf.bellman_ford(
            g, m[0], ogdf.EdgeArrayInt(g, 2**31 - 1), ogdf.NodeArrayInt(g)
        )


def test_bellman_ford_reports_only_reachable_negative_cycles():
    g, m = ogdf.from_edges([(0, 1), (1, 0)])
    assert not ogdf.bellman_ford(
        g, m[0], ogdf.EdgeArrayInt(g, -1), ogdf.NodeArrayInt(g)
    )
    g, m = ogdf.from_edges([(0, 1), (2, 3), (3, 2)])
    assert ogdf.bellman_ford(g, m[0], ogdf.EdgeArrayInt(g, -1), ogdf.NodeArrayInt(g))


def test_bellman_ford_handles_negative_edges():
    g, m = ogdf.from_edges([(0, 1), (0, 2), (2, 1)])
    length = ogdf.EdgeArrayInt(g)
    for e, value in zip(g.edges(), (4, 2, -3)):
        length[e] = value
    d = ogdf.NodeArrayInt(g)
    assert ogdf.bellman_ford(g, m[0], length, d)
    assert d[m[1]] == -1


# --- C14: NaN ------------------------------------------------------------- #


def test_max_flow_rejects_nan_capacity():
    g, m = ogdf.from_edges([(0, 1)])
    with pytest.raises(PreconditionError, match="NaN"):
        ogdf.max_flow(
            g, ogdf.EdgeArrayDouble(g, math.nan), m[0], m[1], ogdf.EdgeArrayDouble(g)
        )


def test_dijkstra_rejects_nan_weight():
    g, m = ogdf.from_edges([(0, 1)])
    with pytest.raises(PreconditionError, match="NaN"):
        ogdf.dijkstra(
            g, ogdf.EdgeArrayDouble(g, math.nan), m[0], ogdf.NodeArrayDouble(g)
        )


# --- P2: seeds ------------------------------------------------------------ #


def test_every_drawn_seed_is_accepted():
    for _ in range(200):
        seed = ogdf.new_seed()
        assert ogdf.set_seed(seed) == seed


@pytest.mark.parametrize("seed", [2**32, -(2**31) - 1])
def test_out_of_range_seed_raises_value_error(seed):
    with pytest.raises(ValueError):
        ogdf.set_seed(seed)


def test_seeds_above_int32_are_reproducible():
    def draw(seed):
        g = ogdf.Graph()
        with ogdf.seeded(seed):
            ogdf.random_graph(g, 20, 40)
        return ogdf.to_edges(g)

    assert draw(2**32 - 5) == draw(2**32 - 5)


# --- P3: to_networkx directedness ----------------------------------------- #


def test_to_networkx_is_undirected_unless_asked():
    nx = pytest.importorskip("networkx")
    g, _ = ogdf.from_networkx(nx.path_graph(3))
    ga = ogdf.GraphAttributes(g)
    assert ga.directed  # OGDF's default, which must not leak into the result
    assert type(ogdf.to_networkx(g, ga)) is nx.Graph
    assert type(ogdf.to_networkx(g, ga, directed=True)) is nx.DiGraph
