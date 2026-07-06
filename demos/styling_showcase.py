"""Style a graph: node colors by degree, shapes, labels, and edge arrows."""

from _common import output_dir, palette

import ogdf


def main():
    out = output_dir()

    g = ogdf.Graph()
    ogdf.wheel_graph(g, 12)  # a hub plus a 12-node rim -> varied degrees

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)

    # Color each node by its degree, and make higher-degree nodes larger.
    degrees = [v.degree for v in g.nodes()]
    max_degree = max(degrees)
    colors = palette(max_degree + 1)
    for v in g.nodes():
        ga.set_fill_color(v, colors[v.degree])
        ga.set_node_stroke_color(v, ogdf.Color(40, 40, 40))
        ga.set_node_stroke_width(v, 1.5)
        size = 20.0 + 4.0 * v.degree
        ga.set_width(v, size)
        ga.set_height(v, size)
        ga.set_shape(v, ogdf.Shape.ELLIPSE)
        ga.set_node_label(v, str(v.index))

    # Directed-looking edges with an arrowhead and a soft gray stroke.
    for e in g.edges():
        ga.set_arrow(e, ogdf.EdgeArrow.LAST)
        ga.set_edge_stroke_color(e, ogdf.Color(120, 120, 120))
        ga.set_edge_stroke_width(e, 1.5)

    path = out / "styling_wheel.svg"
    ogdf.draw_svg(ga, str(path))
    print("Styling showcase:")
    print(f"  wheel graph, colored by degree (max {max_degree}) -> {path.name}")


if __name__ == "__main__":
    main()
