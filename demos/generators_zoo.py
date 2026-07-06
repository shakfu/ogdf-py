"""Generate a variety of named graphs and render each to SVG."""

from _common import output_dir

import ogdf

GENERATORS = [
    ("complete_k6", lambda g: ogdf.complete_graph(g, 6)),
    ("bipartite_k3_4", lambda g: ogdf.complete_bipartite_graph(g, 3, 4)),
    ("wheel_10", lambda g: ogdf.wheel_graph(g, 10)),
    ("cube_3", lambda g: ogdf.cube_graph(g, 3)),
    ("grid_5x5", lambda g: ogdf.grid_graph(g, 5, 5)),
    ("petersen", lambda g: ogdf.petersen_graph(g)),
    ("regular_tree", lambda g: ogdf.regular_tree(g, 15, 2)),
    ("random_regular_3", lambda g: ogdf.random_regular_graph(g, 12, 3)),
]


def main():
    out = output_dir()
    print("Generator zoo:")
    for name, generate in GENERATORS:
        g = ogdf.Graph()
        generate(g)
        ga = ogdf.GraphAttributes(g)
        ogdf.FMMMLayout().call(ga)
        path = out / f"generator_{name}.svg"
        ogdf.draw_svg(ga, str(path))
        print(
            f"  {name:18s} {g.number_of_nodes():3d} nodes "
            f"{g.number_of_edges():3d} edges -> {path.name}"
        )


if __name__ == "__main__":
    main()
