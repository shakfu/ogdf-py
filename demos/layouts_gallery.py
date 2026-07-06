"""Render the same graph with every layout algorithm, one SVG per layout."""

from _common import output_dir

import ogdf


def planar_graph():
    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 30, 50)
    return g


def tree_graph():
    g = ogdf.Graph()
    ogdf.random_tree(g, 24)
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


if __name__ == "__main__":
    main()
