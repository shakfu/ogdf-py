"""Generate a variety of named graphs and render each to SVG."""

from _common import output_dir

import ogdf

def _hexagonal_prism(g):
    """Cartesian product C6 x K2 = a hexagonal prism."""
    cycle = ogdf.Graph()
    nodes = [cycle.new_node() for _ in range(6)]
    for i in range(6):
        cycle.new_edge(nodes[i], nodes[(i + 1) % 6])
    edge = ogdf.Graph()
    ogdf.complete_graph(edge, 2)
    ogdf.cartesian_product(cycle, edge, g)


GENERATORS = [
    ("complete_k6", lambda g: ogdf.complete_graph(g, 6)),
    ("bipartite_k3_4", lambda g: ogdf.complete_bipartite_graph(g, 3, 4)),
    ("wheel_10", lambda g: ogdf.wheel_graph(g, 10)),
    ("cube_3", lambda g: ogdf.cube_graph(g, 3)),
    ("grid_5x5", lambda g: ogdf.grid_graph(g, 5, 5)),
    ("petersen", lambda g: ogdf.petersen_graph(g)),
    ("regular_tree", lambda g: ogdf.regular_tree(g, 15, 2)),
    ("circulant_12", lambda g: ogdf.circulant_graph(g, 12, [1, 3, 5])),
    ("hexagonal_prism", _hexagonal_prism),
    ("watts_strogatz", lambda g: ogdf.random_watts_strogatz_graph(g, 20, 4, 0.15)),
    ("preferential_attachment", lambda g: ogdf.preferential_attachment_graph(g, 25, 2)),
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
