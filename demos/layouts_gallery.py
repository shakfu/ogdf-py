"""Render the same graph with every layout algorithm, one SVG per layout."""

from _common import output_dir

import ogdf


def planar_graph():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 30, 50)
    return g


def large_graph():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 60, 100)
    return g


def tree_graph():
    g = ogdf.Graph()
    ogdf.random_tree(g, 24)
    return g


def triconnected_graph():
    g = ogdf.Graph()
    ogdf.wheel_graph(g, 14)  # a wheel is 3-connected and planar
    return g


def dag():
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(12)]
    for i in range(len(nodes) - 1):
        g.new_edge(nodes[i], nodes[i + 1])
    g.new_edge(nodes[0], nodes[6])
    g.new_edge(nodes[2], nodes[9])
    return g


def linear_graph():
    # An arc diagram reads best with few, ordered nodes: a backbone path plus a
    # handful of longer chords.
    g = ogdf.Graph()
    nodes = [g.new_node() for _ in range(16)]
    for i in range(len(nodes) - 1):
        g.new_edge(nodes[i], nodes[i + 1])
    for a, b in [(0, 6), (2, 11), (4, 15), (7, 13), (1, 9), (5, 12)]:
        g.new_edge(nodes[a], nodes[b])
    return g


# (name, layout factory, graph factory)
LAYOUTS = [
    ("sugiyama", ogdf.SugiyamaLayout, planar_graph),
    ("fmmm", ogdf.FMMMLayout, planar_graph),
    ("gem", ogdf.GEMLayout, planar_graph),
    ("spring_kk", ogdf.SpringEmbedderKK, planar_graph),
    ("stress_minimization", ogdf.StressMinimization, planar_graph),
    ("pivot_mds", ogdf.PivotMDS, planar_graph),
    ("schnyder", ogdf.SchnyderLayout, planar_graph),
    ("circular", ogdf.CircularLayout, planar_graph),
    ("tree", ogdf.TreeLayout, tree_graph),
    ("radial_tree", ogdf.RadialTreeLayout, tree_graph),
    ("tutte", ogdf.TutteLayout, triconnected_graph),
    ("dominance", ogdf.DominanceLayout, dag),
    ("visibility", ogdf.VisibilityLayout, dag),
    ("multilevel", ogdf.MultilevelLayout, large_graph),
    ("balloon", ogdf.BalloonLayout, planar_graph),
]


def main():
    out = output_dir()
    print("Layout gallery:")
    for name, make_layout, make_graph in LAYOUTS:
        g = make_graph()
        ga = ogdf.GraphAttributes(g)
        try:
            make_layout().call(ga)
            path = out / f"layout_{name}.svg"
            ogdf.draw_svg(ga, str(path))
            print(f"  {name:22s} -> {path.name}")
        except Exception as exc:  # noqa: BLE001 - demos report and continue
            print(f"  {name:22s} FAILED: {exc}")

    # The orthogonal (right-angle) planarization layout is configured, not a
    # plain class, so it gets its own entry.
    g = planar_graph()
    ga = ogdf.GraphAttributes(g)
    layout = ogdf.PlanarizationLayout()
    layout.use_orthogonal_layout(30.0)
    layout.call(ga)
    path = out / "layout_orthogonal.svg"
    ogdf.draw_svg(ga, str(path))
    print(f"  {'orthogonal':22s} -> {path.name}")

    # Linear (arc diagram): LinearLayout spreads nodes across a fixed width of
    # 100 regardless of node size, so shrink the node boxes to keep them from
    # overlapping into a solid bar.
    g = linear_graph()
    ga = ogdf.GraphAttributes(g)
    for v in g.nodes():
        ga.set_width(v, 3.0)
        ga.set_height(v, 3.0)
    ogdf.LinearLayout().call(ga)
    path = out / "layout_linear.svg"
    ogdf.draw_svg(ga, str(path))
    print(f"  {'linear':22s} -> {path.name}")


if __name__ == "__main__":
    main()
