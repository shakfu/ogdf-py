"""Conversion between OGDF graphs and ordinary Python data."""

import pytest

import ogdf

nx = pytest.importorskip("networkx")


# --------------------------------------------------------------------------- #
# Edge lists                                                                   #
# --------------------------------------------------------------------------- #


def test_from_edges_creates_nodes_on_first_mention():
    g, mapping = ogdf.from_edges([("a", "b"), ("b", "c")])
    assert g.number_of_nodes() == 3
    assert g.number_of_edges() == 2
    assert set(mapping) == {"a", "b", "c"}
    assert mapping["b"].degree == 2


def test_from_edges_accepts_isolated_nodes_and_extra_tuple_entries():
    # A weighted edge list (u, v, w) works unchanged; the weight is ignored here.
    g, mapping = ogdf.from_edges([("a", "b", 2.5)], nodes=["z"])
    assert g.number_of_nodes() == 3
    assert mapping["z"].degree == 0


def test_from_edges_preserves_parallel_edges_and_self_loops():
    g, _ = ogdf.from_edges([("a", "b"), ("a", "b"), ("a", "a")])
    assert g.number_of_edges() == 3


def test_from_edges_rejects_a_short_pair():
    with pytest.raises(ValueError, match="source and a target"):
        ogdf.from_edges([("a",)])


def test_edge_list_round_trip():
    edges = [("a", "b"), ("b", "c"), ("c", "a")]
    g, mapping = ogdf.from_edges(edges)
    keys = {v: k for k, v in mapping.items()}
    assert ogdf.to_edges(g, keys=keys) == edges


def test_to_edges_defaults_to_node_index():
    g, _ = ogdf.from_edges([("a", "b")])
    assert ogdf.to_edges(g) == [(0, 1)]


# --------------------------------------------------------------------------- #
# Arrays <-> Python containers                                                 #
# --------------------------------------------------------------------------- #


def test_node_array_to_dict_and_list():
    g, mapping = ogdf.from_edges([("a", "b"), ("b", "c")])
    array = ogdf.NodeArrayInt(g, 0)
    for i, v in enumerate(g.nodes()):
        array[v] = i
    assert ogdf.node_array_to_dict(array, g) == {0: 0, 1: 1, 2: 2}
    keys = {v: k for k, v in mapping.items()}
    assert ogdf.node_array_to_dict(array, g, keys=keys) == {"a": 0, "b": 1, "c": 2}
    assert ogdf.node_array_to_list(array, g) == [0, 1, 2]


def test_edge_array_to_dict_and_list():
    g, _ = ogdf.from_edges([("a", "b"), ("b", "c")])
    array = ogdf.EdgeArrayDouble(g, 1.5)
    assert ogdf.edge_array_to_dict(array, g) == {0: 1.5, 1: 1.5}
    assert ogdf.edge_array_to_list(array, g) == [1.5, 1.5]


def test_fill_node_array_from_mapping_leaves_missing_nodes_alone():
    g, mapping = ogdf.from_edges([("a", "b")])
    keys = {v: k for k, v in mapping.items()}
    array = ogdf.NodeArrayDouble(g, -1.0)
    ogdf.fill_node_array(array, {"a": 1.5}, g, keys=keys)
    assert array[mapping["a"]] == 1.5
    assert array[mapping["b"]] == -1.0


def test_fill_node_array_from_sequence():
    g, _ = ogdf.from_edges([("a", "b"), ("b", "c")])
    array = ogdf.NodeArrayInt(g, 0)
    ogdf.fill_node_array(array, [10, 20, 30], g)
    assert ogdf.node_array_to_list(array, g) == [10, 20, 30]


def test_fill_array_rejects_a_wrong_length_sequence():
    g, _ = ogdf.from_edges([("a", "b")])
    with pytest.raises(ValueError, match="expected 2 values"):
        ogdf.fill_node_array(ogdf.NodeArrayInt(g), [1], g)


def test_fill_edge_array_round_trips_through_a_dict():
    g, _ = ogdf.from_edges([("a", "b"), ("b", "c")])
    array = ogdf.EdgeArrayDouble(g, 0.0)
    ogdf.fill_edge_array(array, {0: 2.0, 1: 3.0}, g)
    assert ogdf.edge_array_to_dict(array, g) == {0: 2.0, 1: 3.0}


# --------------------------------------------------------------------------- #
# Results as ordinary collections                                              #
# --------------------------------------------------------------------------- #


def test_spanning_tree_as_an_edge_list():
    g = ogdf.Graph()
    ogdf.complete_graph(g, 5)
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    in_tree = ogdf.EdgeArrayBool(g)
    ogdf.min_spanning_tree(g, weight, in_tree)
    tree = ogdf.edges_where(in_tree, g)
    assert len(tree) == 4  # n - 1 for a connected graph


def test_nodes_where_returns_nodes_in_order():
    g, mapping = ogdf.from_edges([("a", "b"), ("b", "c")])
    flags = ogdf.NodeArrayBool(g, False)
    flags[mapping["a"]] = True
    flags[mapping["c"]] = True
    assert ogdf.nodes_where(flags, g) == [mapping["a"], mapping["c"]]


# --------------------------------------------------------------------------- #
# NetworkX                                                                     #
# --------------------------------------------------------------------------- #


def test_from_networkx_preserves_counts():
    h = nx.cycle_graph(6)
    g, mapping = ogdf.from_networkx(h)
    assert g.number_of_nodes() == h.number_of_nodes()
    assert g.number_of_edges() == h.number_of_edges()
    assert set(mapping) == set(h.nodes())


def test_from_networkx_preserves_multigraph_edges_and_self_loops():
    h = nx.MultiGraph()
    h.add_edges_from([(1, 2), (1, 2), (3, 3)])
    g, _ = ogdf.from_networkx(h)
    assert g.number_of_edges() == 3


def test_from_networkx_with_attributes_and_labels():
    h = nx.Graph()
    h.add_node("x", name="first")
    h.add_node("y", name="second")
    h.add_edge("x", "y")
    g, ga, mapping = ogdf.from_networkx(
        h, graph_attributes=True, label_attribute="name"
    )
    assert ga.directed is False
    assert ga.node_label(mapping["x"]) == "first"


def test_from_networkx_marks_a_digraph_as_directed():
    _, ga, _ = ogdf.from_networkx(nx.DiGraph([(1, 2)]), graph_attributes=True)
    assert ga.directed is True


def test_to_networkx_round_trip_preserves_structure():
    h = nx.cycle_graph(6)
    g, _ = ogdf.from_networkx(h)
    back = ogdf.to_networkx(g)
    assert back.number_of_nodes() == 6
    assert back.number_of_edges() == 6
    assert nx.is_isomorphic(back, h)


def test_to_networkx_chooses_a_multigraph_when_needed():
    g, _ = ogdf.from_edges([("a", "b"), ("a", "b")])
    back = ogdf.to_networkx(g)
    assert back.is_multigraph()
    assert back.number_of_edges() == 2


def test_to_networkx_carries_layout_coordinates():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 12, 20)
    ga = ogdf.GraphAttributes(g)
    ogdf.FMMMLayout().call(ga)
    back = ogdf.to_networkx(g, ga)
    positions = {n: (d["x"], d["y"]) for n, d in back.nodes(data=True)}
    assert len(positions) == 12
    assert any(x != 0.0 or y != 0.0 for x, y in positions.values())


def test_to_networkx_uses_caller_keys():
    g, mapping = ogdf.from_edges([("a", "b")])
    back = ogdf.to_networkx(g, keys={v: k for k, v in mapping.items()})
    assert set(back.nodes()) == {"a", "b"}


def test_networkx_to_ogdf_to_svg_end_to_end():
    # The workflow the interop layer exists for: NetworkX data in, drawing out.
    h = nx.les_miserables_graph()
    g, ga, mapping = ogdf.from_networkx(
        h, graph_attributes=True, label_attribute="__node__"
    )
    ogdf.FMMMLayout().call(ga)
    svg = ogdf.to_svg(ga)
    assert svg.startswith("<?xml")
    assert g.number_of_nodes() == h.number_of_nodes()
