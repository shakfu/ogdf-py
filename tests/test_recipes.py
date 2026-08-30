"""The four end-to-end recipes from docs/recipes.md, run for real.

These exist so the documented workflows cannot silently break. Each test mirrors
one recipe; if a recipe changes, change it here too.
"""

import pytest

import ogdf

nx = pytest.importorskip("networkx")


def test_recipe_networkx_to_svg(tmp_path):
    h = nx.les_miserables_graph()
    g, ga, mapping = ogdf.from_networkx(
        h, graph_attributes=True, label_attribute="__node__"
    )
    for key, v in mapping.items():
        radius = 8.0 + 2.0 * h.degree(key)
        ga.set_width(v, radius)
        ga.set_height(v, radius)

    with ogdf.seeded(20260831):
        layout = ogdf.FMMMLayout()
        layout.set_unit_edge_length(30.0)
        layout.call(ga)
        # Provenance is recorded inside the block: `seeded` restores the
        # previous seed on exit, so afterwards get_seed() no longer reports it.
        provenance = ogdf.provenance(algorithm="FMMMLayout")

    out = tmp_path / "lesmis.svg"
    assert ogdf.draw_svg(ga, str(out))
    assert out.stat().st_size > 0
    assert provenance["seed"] == 20260831

    back = ogdf.to_networkx(g, ga)
    pos = {n: (d["x"], d["y"]) for n, d in back.nodes(data=True)}
    assert len(pos) == h.number_of_nodes()


def test_recipe_dag_to_layered_svg(tmp_path):
    dependencies = [
        ("app", "http"),
        ("app", "db"),
        ("http", "tls"),
        ("http", "sockets"),
        ("db", "sockets"),
        ("tls", "crypto"),
    ]
    g, mapping = ogdf.from_edges(dependencies)
    ogdf.check("topological_numbering", g)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ga.directed = True
    for key, v in mapping.items():
        ga.set_node_label(v, key)
        ga.set_width(v, 60.0)
        ga.set_height(v, 24.0)
        ga.set_fill_color(v, ogdf.Color(235, 240, 250))
    for e in g.edges():
        ga.set_arrow(e, ogdf.EdgeArrow.LAST)

    layout = ogdf.SugiyamaLayout()
    layout.set_arrange_ccs(True)
    layout.call(ga)
    assert layout.number_of_crossings() >= 0
    assert layout.number_of_levels() > 0
    assert ogdf.draw_svg(ga, str(tmp_path / "dependencies.svg"))

    order = ogdf.NodeArrayInt(g)
    ogdf.topological_numbering(g, order)
    keys = {v: k for k, v in mapping.items()}
    # An edge points from a component to what it depends on, so a valid build
    # order is the reverse topological numbering.
    build_order = [
        keys[v] for v in sorted(g.nodes(), key=lambda v: order[v], reverse=True)
    ]
    for dependent, dependency in dependencies:
        assert build_order.index(dependency) < build_order.index(dependent)


def test_recipe_planar_to_tikz(tmp_path):
    g = ogdf.Graph()
    with ogdf.seeded(7):
        ogdf.random_planar_triconnected_graph(g, 24, 48)

    layout = (
        ogdf.TutteLayout()
        if ogdf.is_valid_for("TutteLayout", g)
        else ogdf.PlanarStraightLayout()
    )
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    for v in g.nodes():
        ga.set_width(v, 10.0)
        ga.set_height(v, 10.0)
        ga.set_fill_color(v, ogdf.Color(70, 110, 200))
    layout.call(ga)

    tikz = ogdf.to_tikz(ga)
    assert "tikzpicture" in tikz
    (tmp_path / "planar.tex").write_text(tikz)
    # The point of a planar layout: the graph really is drawable without them.
    assert ogdf.crossing_number(g) == 0


def test_recipe_weighted_graph_annotated(tmp_path):
    g, mapping = ogdf.from_edges(
        [
            ("a", "b", 4),
            ("b", "c", 1),
            ("c", "d", 3),
            ("d", "a", 2),
            ("a", "c", 5),
            ("b", "d", 6),
        ]
    )
    keys = {v: k for k, v in mapping.items()}

    weight = ogdf.EdgeArrayDouble(g, 1.0)
    ogdf.fill_edge_array(weight, [4, 1, 3, 2, 5, 6], g)

    in_tree = ogdf.EdgeArrayBool(g)
    total = ogdf.min_spanning_tree(g, weight, in_tree)
    tree_edges = ogdf.edges_where(in_tree, g)

    # Cheapest spanning tree of this graph: b-c (1), d-a (2), c-d (3).
    assert total == 6.0
    assert {frozenset((keys[e.source], keys[e.target])) for e in tree_edges} == {
        frozenset(("b", "c")),
        frozenset(("c", "d")),
        frozenset(("d", "a")),
    }

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    for key, v in mapping.items():
        ga.set_node_label(v, key)
        ga.set_width(v, 24.0)
        ga.set_height(v, 24.0)
    for e in g.edges():
        ga.set_edge_label(e, str(int(weight[e])))
        if in_tree[e]:
            ga.set_edge_stroke_color(e, ogdf.Color(200, 60, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(200, 200, 200))

    ogdf.FMMMLayout().call(ga)
    assert ogdf.draw_svg(ga, str(tmp_path / "mst.svg"))
