# ogdf-py

Python bindings for the [Open Graph Drawing Framework (OGDF)](https://ogdf.github.io/), built with [nanobind](https://nanobind.readthedocs.io/).

This is a curated subset of OGDF, not a full wrapper: enough to build graphs, run layout and core graph algorithms, style and draw them, and read/write common graph file formats.

## Quick Start

```bash
make bootstrap   # clone OGDF at the pinned tag and build it from source (once)
uv sync          # build the extension
uv run pytest    # run the tests
uv build         # build a wheel
```

`make build` (and `make sync`) run the bootstrap automatically if OGDF has not been built yet. Use `make help` for additional targets.

## Example

```python
import ogdf

# Build a graph.
g = ogdf.Graph()
ogdf.random_planar_connected_graph(g, 30, 45)

# Attach drawing attributes and run a force-directed layout.
ga = ogdf.GraphAttributes(g)
ogdf.FMMMLayout().call(ga)

# Export to SVG.
ogdf.draw_svg(ga, "graph.svg")
```

Algorithms operate on the same `Graph`, writing per-node/edge results into an array you pass in:

```python
g = ogdf.Graph()
ogdf.complete_bipartite_graph(g, 3, 4)
assert ogdf.is_bipartite(g)

component = ogdf.NodeArrayInt(g)
n = ogdf.connected_components(g, component)   # -> number of components
```

## What's included

- **Graph model:** `Graph`, `Node`, `Edge`, node/edge iteration.

- **Attribute arrays:** `NodeArray` / `EdgeArray` in int, double, and bool.

- **Attributes:** `GraphAttributes` with coordinates, size, labels, and full styling (colors, shapes, fill patterns, stroke, edge arrows, and bends).

- **Layouts:** `SugiyamaLayout` (layered), `FMMMLayout` / `GEMLayout` / `SpringEmbedderKK` (force-directed), `StressMinimization` / `PivotMDS` (stress/MDS), `PlanarizationLayout` (with optional orthogonal routing), `SchnyderLayout` (planar straight-line), `TreeLayout`, `CircularLayout`.

- **Algorithms:** connectivity and structure tests (`is_connected`, `is_biconnected`, `is_bipartite`, `is_acyclic`, `is_planar`, ...), connected / strongly-connected / biconnected components, topological numbering, shortest paths (`dijkstra`), minimum spanning tree, maximum flow, global minimum cut, matching, node coloring, and planar embedding.

- **Generators:** complete, complete-bipartite, wheel, cube, grid, Petersen, regular tree, plus random graphs, trees, digraphs, and regular / biconnected / planar variants.

- **File I/O:** interchange formats GML, GraphML, DOT, GEXF, GDF, TLP (plus extension-based `read`/`write`), and drawing output as SVG and TikZ.

## Demos

```bash
make demos   # writes SVGs and data files to build/demo-output/
```

The demos exercise layouts, styling, algorithm visualizations, generators, and file I/O, and assemble every drawing into `build/demo-output/index.html` for a side-by-side view. See [`demos/README.md`](demos/README.md) for details.

## How it builds

`scripts/bootstrap_ogdf.sh` shallow-clones OGDF at a pinned release tag (`foxglove-202510`) into `thirdparty/ogdf` and builds its static libraries from source. The extension then links `libOGDF.a` / `libCOIN.a` statically, so wheels are self-contained. Because OGDF is prebuilt once (a couple of minutes), rebuilding the bindings only recompiles `_core.cpp` and is fast.

The pin can be overridden: `scripts/bootstrap_ogdf.sh --tag <tag>` or `OGDF_TAG=<tag> make bootstrap`. In CI, run the bootstrap once per platform (e.g. in `cibuildwheel`'s `CIBW_BEFORE_ALL`) so OGDF is reused across all Python versions.
