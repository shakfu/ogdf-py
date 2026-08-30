"""Exception taxonomy and precondition enforcement."""

import pytest

import ogdf


# --------------------------------------------------------------------------- #
# Taxonomy                                                                     #
# --------------------------------------------------------------------------- #


def test_exception_hierarchy():
    assert issubclass(ogdf.OGDFError, Exception)
    assert issubclass(ogdf.PreconditionError, ogdf.OGDFError)
    assert issubclass(ogdf.InvalidGraphError, ogdf.PreconditionError)
    assert issubclass(ogdf.UnsupportedFormatError, ogdf.OGDFError)
    assert issubclass(ogdf.AlgorithmError, ogdf.OGDFError)


def test_argument_errors_remain_value_errors():
    # Code written against earlier versions caught ValueError; keep it working.
    assert issubclass(ogdf.PreconditionError, ValueError)
    assert issubclass(ogdf.InvalidGraphError, ValueError)
    assert issubclass(ogdf.UnsupportedFormatError, ValueError)
    assert issubclass(ogdf.AlgorithmError, RuntimeError)


# --------------------------------------------------------------------------- #
# Layout preconditions                                                         #
# --------------------------------------------------------------------------- #


def _complete(n):
    g = ogdf.Graph()
    ogdf.complete_graph(g, n)
    return g


def _path(n):
    g = ogdf.Graph()
    prev = None
    for _ in range(n):
        v = g.new_node()
        if prev is not None:
            g.new_edge(prev, v)
        prev = v
    return g


def test_schnyder_rejects_non_planar():
    ga = ogdf.GraphAttributes(_complete(5))
    with pytest.raises(ogdf.InvalidGraphError, match="planar"):
        ogdf.SchnyderLayout().call(ga)


def test_tutte_rejects_non_triconnected():
    ga = ogdf.GraphAttributes(_path(5))
    with pytest.raises(ogdf.InvalidGraphError, match="triconnected"):
        ogdf.TutteLayout().call(ga)


def test_tree_layout_rejects_cycle():
    g = _complete(4)
    ga = ogdf.GraphAttributes(g)
    with pytest.raises(ogdf.InvalidGraphError, match="tree or forest"):
        ogdf.TreeLayout().call(ga)


def test_radial_tree_layout_rejects_forest():
    # Two disjoint edges: a forest, but not a tree.
    g = ogdf.Graph()
    a, b, c, d = (g.new_node() for _ in range(4))
    g.new_edge(a, b)
    g.new_edge(c, d)
    with pytest.raises(ogdf.InvalidGraphError, match="tree"):
        ogdf.RadialTreeLayout().call(ogdf.GraphAttributes(g))


def test_upward_layouts_reject_cycles():
    g = ogdf.Graph()
    a, b, c = (g.new_node() for _ in range(3))
    g.new_edge(a, b)
    g.new_edge(b, c)
    g.new_edge(c, a)
    for layout in (ogdf.DominanceLayout(), ogdf.VisibilityLayout()):
        with pytest.raises(ogdf.InvalidGraphError, match="acyclic"):
            layout.call(ogdf.GraphAttributes(g))


def test_spring_embedder_kk_rejects_disconnected():
    g = ogdf.Graph()
    g.new_node()
    g.new_node()
    with pytest.raises(ogdf.InvalidGraphError, match="connected"):
        ogdf.SpringEmbedderKK().call(ogdf.GraphAttributes(g))


def test_balloon_layout_rejects_disconnected():
    g = ogdf.Graph()
    g.new_node()
    g.new_node()
    with pytest.raises(ogdf.InvalidGraphError, match="connected"):
        ogdf.BalloonLayout().call(ogdf.GraphAttributes(g))


def test_valid_input_still_works():
    # The guards must not reject graphs that satisfy the preconditions.
    g = ogdf.Graph()
    ogdf.random_planar_triconnected_graph(g, 12, 24)
    ga = ogdf.GraphAttributes(g)
    ogdf.SchnyderLayout().call(ga)
    assert any(ga.x(v) != 0.0 or ga.y(v) != 0.0 for v in g.nodes())


# --------------------------------------------------------------------------- #
# Algorithm preconditions                                                      #
# --------------------------------------------------------------------------- #


def test_triangulate_requires_an_embedding():
    # K5's adjacency order is not a planar embedding (it cannot be: K5 is not
    # planar), which is exactly the case that used to corrupt the graph.
    k5 = _complete(5)
    assert not ogdf.represents_comb_embedding(k5)
    with pytest.raises(ogdf.InvalidGraphError, match="embedded"):
        ogdf.triangulate(k5)


def test_triangulate_accepts_an_embedded_planar_graph():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 10, 15)
    ogdf.planar_embed(g)
    before = g.number_of_edges()
    ogdf.triangulate(g)
    assert g.number_of_edges() >= before


def test_topological_numbering_requires_a_dag():
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()
    g.new_edge(a, b)
    g.new_edge(b, a)
    with pytest.raises(ogdf.InvalidGraphError, match="acyclic"):
        ogdf.topological_numbering(g, ogdf.NodeArrayInt(g))


def test_dijkstra_rejects_negative_weights():
    g = _path(4)
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    for e in g.edges():
        weight[e] = -1.0
        break
    with pytest.raises(ogdf.PreconditionError, match="non-negative"):
        ogdf.dijkstra(g, weight, next(iter(g.nodes())), ogdf.NodeArrayDouble(g))


def test_array_from_another_graph_is_rejected():
    g1, g2 = _path(4), _path(4)
    weight = ogdf.EdgeArrayDouble(g2, 1.0)
    with pytest.raises(ogdf.PreconditionError, match="different graph"):
        ogdf.dijkstra(g1, weight, next(iter(g1.nodes())), ogdf.NodeArrayDouble(g1))


def test_max_flow_requires_distinct_endpoints():
    g = _path(4)
    s = next(iter(g.nodes()))
    cap = ogdf.EdgeArrayDouble(g, 1.0)
    with pytest.raises(ogdf.PreconditionError, match="distinct"):
        ogdf.max_flow(g, cap, s, s, ogdf.EdgeArrayDouble(g))


def test_unsupported_write_format():
    ga = ogdf.GraphAttributes(_path(3))
    with pytest.raises(ogdf.UnsupportedFormatError):
        ogdf.write(ga, "graph.leda")


def test_bipartite_matching_rejects_odd_cycle():
    g = ogdf.Graph()
    a, b, c = (g.new_node() for _ in range(3))
    g.new_edge(a, b)
    g.new_edge(b, c)
    g.new_edge(c, a)
    with pytest.raises(ogdf.InvalidGraphError, match="bipartite"):
        ogdf.maximum_matching_bipartite(g, ogdf.EdgeArrayBool(g))


# --------------------------------------------------------------------------- #
# Validation helpers                                                           #
# --------------------------------------------------------------------------- #


def test_requirements_and_validate_agree_with_enforcement():
    g = _complete(5)  # K5: simple, triconnected, not planar
    assert "planar" in " ".join(ogdf.requirements("SchnyderLayout"))
    assert ogdf.validate("SchnyderLayout", g) == ["planar"]
    assert not ogdf.is_valid_for("SchnyderLayout", g)
    with pytest.raises(ogdf.InvalidGraphError):
        ogdf.check("SchnyderLayout", g)
    # And the operation itself rejects it for exactly that reason.
    with pytest.raises(ogdf.InvalidGraphError, match="planar"):
        ogdf.SchnyderLayout().call(ogdf.GraphAttributes(g))


def test_validate_passes_for_a_conforming_graph():
    g = ogdf.Graph()
    ogdf.random_planar_triconnected_graph(g, 12, 24)
    assert ogdf.validate("SchnyderLayout", g) == []
    assert ogdf.is_valid_for("SchnyderLayout", g)
    ogdf.check("SchnyderLayout", g)  # does not raise


def test_validate_reports_every_unmet_requirement():
    # K5 plus an isolated node is neither planar nor triconnected; validate()
    # reports both rather than stopping at the first failure.
    g = _complete(5)
    g.new_node()
    unmet = ogdf.validate("TutteLayout", g)
    assert unmet == ["planar", "triconnected"]


def test_unknown_operation_lists_the_known_ones():
    with pytest.raises(KeyError, match="no recorded graph preconditions"):
        ogdf.requirements("NoSuchLayout")
    assert "TutteLayout" in ogdf.operations()


def test_graph_report_describes_a_known_graph():
    g = _path(4)
    report = ogdf.graph_report(g)
    assert report["nodes"] == 4
    assert report["edges"] == 3
    assert report["connected"] is True
    assert report["tree"] is True
    assert report["forest"] is True
    assert report["planar"] is True
    assert report["triconnected"] is False
