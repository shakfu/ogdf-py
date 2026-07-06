# ogdf-py

Python bindings for the [Open Graph Drawing Framework (OGDF)](https://ogdf.github.io/), built with [nanobind](https://nanobind.readthedocs.io/).

This is a **curated subset** of OGDF, not a full wrapper: enough to build graphs, run layout and core graph algorithms, style and draw them, and read/write common graph file formats. See [Coverage](coverage.md) for exactly what is and is not included.

## Install

```bash
pip install ogdf-py
```

Binary wheels are published for Linux (x86_64, aarch64) and macOS (x86_64, arm64) on CPython 3.10-3.13.

## Example

```python
import ogdf

# Build a graph and run a force-directed layout.
g = ogdf.Graph()
ogdf.random_planar_connected_graph(g, 30, 45)
ga = ogdf.GraphAttributes(g)
ogdf.FMMMLayout().call(ga)

# Export to SVG.
ogdf.draw_svg(ga, "graph.svg")
```

## What's included

- **Graph model** - `Graph`, `Node`, `Edge`, node/edge iteration, and `NodeArray`/`EdgeArray` attribute arrays.

- **Attributes & styling** - coordinates, size, labels, colors, shapes, fill patterns, stroke, edge arrows, and bends.

- **Layouts** - layered, force-directed, stress/MDS, planarization, orthogonal, planar straight-line, tree, and circular.

- **Algorithms** - connectivity and structure tests, components, shortest paths, spanning tree, flow, cut, matching, coloring, and planarity.

- **Generators** - complete, bipartite, wheel, cube, grid, Petersen, trees, and several random families.

- **File I/O** - GML, GraphML, DOT, GEXF, GDF, TLP interchange, plus SVG and TikZ drawing output.

See [Getting Started](getting-started.md) for a fuller tour, the
[Gallery](gallery.md) for example drawings, and [Coverage](coverage.md) for
exactly what is included.
