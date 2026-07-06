"""Write a laid-out graph to each file format and read it back."""

from _common import output_dir

import ogdf

FORMATS = [
    ("gml", ogdf.write_gml, ogdf.read_gml),
    ("graphml", ogdf.write_graphml, ogdf.read_graphml),
    ("dot", ogdf.write_dot, ogdf.read_dot),
    ("gexf", ogdf.write_gexf, ogdf.read_gexf),
    ("tlp", ogdf.write_tlp, ogdf.read_tlp),
]


def main():
    out = output_dir()

    g = ogdf.Graph()
    ogdf.random_planar_connected_graph(g, 15, 22)
    ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
    ogdf.FMMMLayout().call(ga)

    print("File I/O round-trips:")
    for ext, write, read in FORMATS:
        path = out / f"io_sample.{ext}"
        write(ga, str(path))

        g2 = ogdf.Graph()
        ga2 = ogdf.GraphAttributes(g2, ogdf.ALL_ATTRIBUTES)
        read(ga2, g2, str(path))

        ok = (
            g2.number_of_nodes() == g.number_of_nodes()
            and g2.number_of_edges() == g.number_of_edges()
        )
        status = "ok" if ok else "MISMATCH"
        print(
            f"  {ext:8s} {path.name:16s} "
            f"read back {g2.number_of_nodes()} nodes / "
            f"{g2.number_of_edges()} edges [{status}]"
        )

    svg = out / "io_sample.svg"
    ogdf.draw_svg(ga, str(svg))
    print(f"  svg      {svg.name:16s} written (drawing)")

    tikz = out / "io_sample.tex"
    ogdf.draw_tikz(ga, str(tikz))
    print(f"  tikz     {tikz.name:16s} written (drawing)")


if __name__ == "__main__":
    main()
