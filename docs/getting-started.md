# Getting Started

## Installation

### From PyPI

```bash
pip install ogdf-py
```

Wheels are available for Linux (x86_64, aarch64), macOS (x86_64, arm64), and Windows (AMD64) on CPython 3.10-3.14. On platforms without a matching wheel, pip falls back to the source distribution, which builds OGDF from source at install time; this needs `git`, a C++17 compiler (MSVC works), CMake, and network access.

### From source

```bash
git clone https://github.com/shakfu/ogdf-py
cd ogdf-py
make bootstrap   # clone OGDF at the pinned tag and build it from source (once)
uv sync          # build the extension
```

`make build` and `make sync` run the bootstrap automatically if OGDF has not been built yet. See `make help` for all targets.

## Building graphs

```python
import ogdf

g = ogdf.Graph()
a, b, c = g.new_node(), g.new_node(), g.new_node()
g.new_edge(a, b)
g.new_edge(b, c)

print(g.number_of_nodes(), g.number_of_edges())   # 3 2
for node in g.nodes():
    print(node.index, node.degree)
```

Generators fill a graph directly:

```python
g = ogdf.Graph()
ogdf.complete_bipartite_graph(g, 3, 4)
```

## Layouts

Every layout writes coordinates into a `GraphAttributes`:

```python
ga = ogdf.GraphAttributes(g)
layout = ogdf.FMMMLayout()
layout.set_unit_edge_length(20.0)
layout.call(ga)
```

## Styling and drawing

Enable the styling attributes, then set colors, shapes, and arrows:

```python
ga = ogdf.GraphAttributes(g, ogdf.ALL_ATTRIBUTES)
ogdf.SugiyamaLayout().call(ga)

for v in g.nodes():
    ga.set_fill_color(v, ogdf.Color(70, 110, 200))
    ga.set_shape(v, ogdf.Shape.ELLIPSE)

svg = ogdf.to_svg(ga)          # or ogdf.draw_svg(ga, "graph.svg")
tikz = ogdf.to_tikz(ga)        # LaTeX / PGF output
```

## Algorithms

Algorithms operate on the `Graph`. Those that produce per-node or per-edge results follow OGDF's idiom: you pass in an array to receive the output, and the function returns the scalar result.

```python
# Connected components -> count, plus a component id per node.
component = ogdf.NodeArrayInt(g)
n = ogdf.connected_components(g, component)

# Shortest paths from a source.
weight = ogdf.EdgeArrayDouble(g, 1.0)
dist = ogdf.NodeArrayDouble(g)
ogdf.dijkstra(g, weight, source, dist)

# Minimum spanning tree.
in_tree = ogdf.EdgeArrayBool(g)
total = ogdf.min_spanning_tree(g, weight, in_tree)
```

## File I/O

```python
ogdf.write_gml(ga, "graph.gml")
ogdf.write_graphml(ga, "graph.graphml")

g2 = ogdf.Graph()
ga2 = ogdf.GraphAttributes(g2, ogdf.ALL_ATTRIBUTES)
ogdf.read_gml(ga2, g2, "graph.gml")
```

The generic `write(ga, filename)` chooses the format from the extension; it raises `ValueError` for formats that cannot store attributes.

## Demos

```bash
make demos
```

This writes example drawings and data files to `build/demo-output/` and builds a self-contained `index.html` gallery.
