"""Tests for GraphAttributes styling (colors, shapes, arrows, bends)."""

import ogdf


def small_graph():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(4)]
    for i in range(3):
        g.new_edge(nodes[i], nodes[i + 1])
    return g, nodes


def test_color_construction_and_accessors():
    c = ogdf.Color(255, 128, 0)
    assert (c.red, c.green, c.blue, c.alpha) == (255, 128, 0, 255)
    c.blue = 64
    assert c.blue == 64

    hexc = ogdf.Color("#00ff00")
    assert (hexc.red, hexc.green, hexc.blue) == (0, 255, 0)


def test_node_fill_and_stroke_color():
    g, nodes = small_graph()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ga.set_fill_color(nodes[0], ogdf.Color(255, 0, 0))
    ga.set_node_stroke_color(nodes[0], ogdf.Color(0, 0, 255))
    fill = ga.fill_color(nodes[0])
    stroke = ga.node_stroke_color(nodes[0])
    assert (fill.red, fill.green, fill.blue) == (255, 0, 0)
    assert (stroke.red, stroke.green, stroke.blue) == (0, 0, 255)


def test_node_shape():
    g, nodes = small_graph()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ga.set_shape(nodes[0], ogdf.Shape.ELLIPSE)
    assert ga.shape(nodes[0]) == ogdf.Shape.ELLIPSE


def test_edge_arrow_and_stroke():
    g, nodes = small_graph()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    e = next(g.edges())
    ga.set_arrow(e, ogdf.EdgeArrow.LAST)
    ga.set_edge_stroke_color(e, ogdf.Color(0, 128, 0))
    assert ga.arrow(e) == ogdf.EdgeArrow.LAST
    color = ga.edge_stroke_color(e)
    assert (color.red, color.green, color.blue) == (0, 128, 0)


def test_edge_bends():
    g, nodes = small_graph()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    e = next(g.edges())
    ga.add_bend(e, 10.0, 20.0)
    ga.add_bend(e, 30.0, 40.0)
    # Bends should render without error.
    svg = ogdf.to_svg(ga)
    assert "<svg" in svg
    ga.clear_bends(e)


def test_styled_svg_contains_color():
    g, nodes = small_graph()
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.SugiyamaLayout().call(ga)
    ga.set_fill_color(nodes[0], ogdf.Color(255, 0, 0))
    svg = ogdf.to_svg(ga).lower()
    # The red fill must appear in the SVG output.
    assert "ff0000" in svg or "rgb(255" in svg
