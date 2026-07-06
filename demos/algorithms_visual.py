"""Visualize algorithm results by coloring nodes and edges."""

import random

from _common import gradient_color, output_dir, palette

import ogdf


def demo_components(out):
    """Three disconnected clusters, colored by connected component."""
    g = ogdf.Graph()
    for _ in range(3):
        nodes = [g.new_node() for _ in range(6)]
        for i in range(6):
            g.new_edge(nodes[i], nodes[(i + 1) % 6])

    comp = ogdf.NodeArrayInt(g)
    k = ogdf.connected_components(g, comp)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    colors = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, colors[comp[v]])

    path = out / "algo_components.svg"
    ogdf.draw_svg(ga, str(path))
    return f"{k} connected components -> {path.name}"


def demo_coloring(out):
    """Proper node coloring, one palette color per color class."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 30, 60)

    colors_arr = ogdf.NodeArrayInt(g)
    k = ogdf.node_coloring(g, colors_arr)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.CircularLayout().call(ga)
    pal = palette(k)
    for v in g.nodes():
        ga.set_fill_color(v, pal[colors_arr[v]])

    path = out / "algo_coloring.svg"
    ogdf.draw_svg(ga, str(path))
    return f"proper coloring with {k} colors -> {path.name}"


def demo_shortest_paths(out):
    """Grid graph shaded by shortest-path distance from a corner node."""
    g = ogdf.Graph()
    ogdf.grid_graph(g, 7, 7)

    source = next(g.nodes())
    weight = ogdf.EdgeArrayDouble(g, 1.0)
    dist = ogdf.NodeArrayDouble(g)
    ogdf.dijkstra(g, weight, source, dist)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    d_max = max(dist[v] for v in g.nodes()) or 1.0
    for v in g.nodes():
        ga.set_fill_color(v, gradient_color(dist[v] / d_max))

    path = out / "algo_shortest_paths.svg"
    ogdf.draw_svg(ga, str(path))
    return f"shortest paths (max distance {d_max:.0f}) -> {path.name}"


def demo_mst(out):
    """Weighted graph with the minimum spanning tree highlighted in green."""
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 24, 40)

    rng = random.Random(7)
    weight = ogdf.EdgeArrayDouble(g)
    for e in g.edges():
        weight[e] = rng.uniform(1.0, 10.0)

    in_tree = ogdf.EdgeArrayBool(g)
    total = ogdf.min_spanning_tree(g, weight, in_tree)

    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)
    for v in g.nodes():
        ga.set_fill_color(v, ogdf.Color(70, 110, 200))
    for e in g.edges():
        if in_tree[e]:
            ga.set_edge_stroke_color(e, ogdf.Color(20, 150, 60))
            ga.set_edge_stroke_width(e, 3.0)
        else:
            ga.set_edge_stroke_color(e, ogdf.Color(210, 210, 210))
            ga.set_edge_stroke_width(e, 1.0)

    path = out / "algo_mst.svg"
    ogdf.draw_svg(ga, str(path))
    return f"minimum spanning tree (weight {total:.1f}) -> {path.name}"


def main():
    out = output_dir()
    print("Algorithm visualizations:")
    for demo in (demo_components, demo_coloring, demo_shortest_paths, demo_mst):
        print(f"  {demo(out)}")


if __name__ == "__main__":
    main()
