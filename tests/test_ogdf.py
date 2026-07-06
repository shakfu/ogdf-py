"""Tests for the OGDF nanobind bindings."""

import pytest

import ogdf


# --------------------------------------------------------------------------- #
# Graph construction and topology                                             #
# --------------------------------------------------------------------------- #
def test_build_graph():
    g = ogdf.Graph()
    assert g.empty()
    a, b, c = g.new_node(), g.new_node(), g.new_node()
    g.new_edge(a, b)
    g.new_edge(b, c)
    assert g.number_of_nodes() == 3
    assert g.number_of_edges() == 2
    assert len(g) == 3
    assert not g.empty()


def test_edge_endpoints():
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()
    e = g.new_edge(a, b)
    assert e.source.index == a.index
    assert e.target.index == b.index


def test_clear():
    g = ogdf.Graph()
    g.new_node()
    g.new_node()
    g.clear()
    assert g.number_of_nodes() == 0
    assert g.empty()


# --------------------------------------------------------------------------- #
# Iteration                                                                   #
# --------------------------------------------------------------------------- #
def test_node_edge_iteration():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(5)]
    for i in range(4):
        g.new_edge(nodes[i], nodes[i + 1])

    assert [n.index for n in g.nodes()] == [0, 1, 2, 3, 4]
    assert [n.index for n in g] == [0, 1, 2, 3, 4]  # __iter__ == nodes
    assert [(e.source.index, e.target.index) for e in g.edges()] == [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
    ]


def test_node_degree():
    g = ogdf.Graph()
    hub, a, b = g.new_node(), g.new_node(), g.new_node()
    g.new_edge(hub, a)
    g.new_edge(hub, b)
    assert hub.degree == 2
    assert a.degree == 1


# --------------------------------------------------------------------------- #
# Attribute arrays                                                            #
# --------------------------------------------------------------------------- #
def test_node_array_int():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(4)]
    arr = ogdf.NodeArrayInt(g, -1)
    for n in nodes:
        arr[n] = n.index * 10
    assert [arr[n] for n in nodes] == [0, 10, 20, 30]


def test_node_array_default_and_fill():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(3)]
    arr = ogdf.NodeArrayDouble(g, 1.5)
    assert all(arr[n] == 1.5 for n in nodes)
    arr.fill(2.0)
    assert all(arr[n] == 2.0 for n in nodes)


def test_edge_array_double():
    g = ogdf.Graph()
    a, b = g.new_node(), g.new_node()
    e = g.new_edge(a, b)
    arr = ogdf.EdgeArrayDouble(g, 0.0)
    arr[e] = 3.14
    assert arr[e] == 3.14


def test_array_autoresizes_with_graph():
    """A registered array tracks nodes added after its construction."""
    g = ogdf.Graph()
    arr = ogdf.NodeArrayInt(g, 7)
    n = g.new_node()  # added after the array exists
    assert arr[n] == 7  # gets the default value


# --------------------------------------------------------------------------- #
# GraphAttributes                                                             #
# --------------------------------------------------------------------------- #
def test_graph_attributes_geometry():
    g = ogdf.Graph()
    n = g.new_node()
    ga = ogdf.GraphAttributes(g)
    ga.set_x(n, 12.0)
    ga.set_y(n, 34.0)
    ga.set_width(n, 50.0)
    ga.set_height(n, 60.0)
    assert ga.x(n) == 12.0
    assert ga.y(n) == 34.0
    assert ga.width(n) == 50.0
    assert ga.height(n) == 60.0


def test_graph_attributes_labels():
    g = ogdf.Graph()
    n = g.new_node()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ga.set_node_label(n, "hello")
    assert ga.node_label(n) == "hello"


# --------------------------------------------------------------------------- #
# Layout algorithms                                                           #
# --------------------------------------------------------------------------- #
def _chain(n):
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(n)]
    for i in range(n - 1):
        g.new_edge(nodes[i], nodes[i + 1])
    return g, nodes


@pytest.mark.parametrize(
    "layout_cls",
    [
        ogdf.SugiyamaLayout,
        ogdf.FMMMLayout,
        ogdf.CircularLayout,
        ogdf.TreeLayout,
    ],
)
def test_layout_assigns_distinct_coordinates(layout_cls):
    g, nodes = _chain(6)
    ga = ogdf.GraphAttributes(g)
    layout_cls().call(ga)
    coords = {(round(ga.x(n), 3), round(ga.y(n), 3)) for n in nodes}
    assert len(coords) == len(nodes)


def test_planarization_orthogonal():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 12, 18)
    ga = ogdf.GraphAttributes(g)
    layout = ogdf.PlanarizationLayout()
    layout.use_orthogonal_layout(30.0)
    layout.call(ga)
    assert ga.bounding_box_width() > 0
    assert ga.bounding_box_height() > 0


def test_layout_configuration():
    g, nodes = _chain(5)
    ga = ogdf.GraphAttributes(g)
    layout = ogdf.SugiyamaLayout()
    layout.set_runs(2)
    layout.set_transpose(True)
    layout.call(ga)  # config setters must not break the call
    assert ga.bounding_box_height() > 0


def test_tree_layout_orientation():
    g = ogdf.Graph()
    root = g.new_node()
    children = [g.new_node() for _ in range(3)]
    for c in children:
        g.new_edge(root, c)
    ga = ogdf.GraphAttributes(g)
    t = ogdf.TreeLayout()
    t.set_orientation(ogdf.Orientation.LEFT_TO_RIGHT)
    t.call(ga)
    # Left-to-right: root should be left of (smaller x than) its children.
    assert all(ga.x(root) < ga.x(c) for c in children)


# --------------------------------------------------------------------------- #
# File I/O                                                                     #
# --------------------------------------------------------------------------- #
def test_svg_string():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 10, 15)
    ga = ogdf.GraphAttributes(g)
    ogdf.SugiyamaLayout().call(ga)
    svg = ogdf.to_svg(ga)
    assert svg.startswith("<?xml")
    assert "<svg" in svg and "</svg>" in svg


def test_svg_file(tmp_path):
    g = ogdf.Graph()
    ogdf.random_graph(g, 8, 10)
    ga = ogdf.GraphAttributes(g)
    ogdf.SugiyamaLayout().call(ga)
    out = tmp_path / "graph.svg"
    assert ogdf.draw_svg(ga, str(out))
    assert out.exists() and out.stat().st_size > 0


@pytest.mark.parametrize(
    "ext,write,read",
    [
        ("gml", ogdf.write_gml, ogdf.read_gml),
        ("graphml", ogdf.write_graphml, ogdf.read_graphml),
        ("dot", ogdf.write_dot, ogdf.read_dot),
        ("gexf", ogdf.write_gexf, ogdf.read_gexf),
        ("gdf", ogdf.write_gdf, ogdf.read_gdf),
        ("tlp", ogdf.write_tlp, ogdf.read_tlp),
    ],
)
def test_io_roundtrip(tmp_path, ext, write, read):
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 10, 15)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)

    path = str(tmp_path / f"graph.{ext}")
    assert write(ga, path)

    g2 = ogdf.Graph()
    ga2 = ogdf.GraphAttributes(g2, ogdf.ALL_ATTRIBUTES)
    assert read(ga2, g2, path)
    assert g2.number_of_nodes() == g.number_of_nodes()
    assert g2.number_of_edges() == g.number_of_edges()


def test_tikz_output():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 8, 12)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    tikz = ogdf.to_tikz(ga)
    assert "tikzpicture" in tikz or "tikz" in tikz.lower()


def test_generic_write_by_extension(tmp_path):
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 8, 12)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    out = tmp_path / "graph.gexf"
    assert ogdf.write(ga, str(out))  # format inferred from extension
    assert out.exists()


def test_generic_write_rejects_attribute_incapable_format(tmp_path):
    # LEDA/Chaco only store plain graphs; writing attributes must raise, not
    # crash the interpreter.
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 8, 12)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    with pytest.raises(ValueError):
        ogdf.write(ga, str(tmp_path / "graph.leda"))
