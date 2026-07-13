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

- **Layouts:** `SugiyamaLayout` (layered), `FMMMLayout` / `GEMLayout` / `SpringEmbedderKK` / `MultilevelLayout` (force-directed), `StressMinimization` / `PivotMDS` (stress/MDS), `PlanarizationLayout` (with optional orthogonal routing), `SchnyderLayout` / `FPPLayout` / `PlanarStraightLayout` / `PlanarDrawLayout` / `MixedModelLayout` (planar straight-line and mixed-model), `TreeLayout` / `RadialTreeLayout` / `BalloonLayout`, `CircularLayout`, `LinearLayout` (arc diagram), `TutteLayout` (convex planar), and `DominanceLayout` / `VisibilityLayout` (upward, for DAGs).

- **Algorithms:** connectivity and structure tests (`is_connected`, `is_biconnected`, `is_bipartite`, `is_acyclic`, `is_planar`, ...), node/edge k-connectivity (`node_connectivity`, `edge_connectivity`), components, cut vertices and bridges, separation pairs and SPQR-tree summary, topological numbering, shortest paths (`dijkstra`, `bellman_ford`, `a_star_search`), minimum spanning tree, maximum flow, minimum-cost flow, global minimum cut and s-t minimum cut (`min_st_cut`), matching (bipartite and maximum-weight), node coloring, minimum Steiner tree, planar embedding, maximal planar subgraph, crossing minimization (`crossing_number`), and edge-insertion routing (`insert_edges`).

- **Generators:** classic graphs (complete, bipartite, wheel, cube, grid, Petersen, circulant, k-partite, globe, lattice), graph products (cartesian, tensor, strong, lexicographical), operations (union, complement, suspension), and random models (Erdos-Renyi, regular, planar, triconnected, Watts-Strogatz, preferential attachment, Chung-Lu, Waxman, geometric, series-parallel DAG, hierarchy).

- **File I/O:** interchange formats GML, GraphML, DOT, GEXF, GDF, TLP (plus extension-based `read`/`write`), and drawing output as SVG and TikZ.

## Demos

```bash
make demos   # writes SVGs and data files to build/demo-output/
```

The demos exercise layouts, styling, algorithm visualizations, generators, and file I/O, and assemble every drawing into `build/demo-output/index.html` for a side-by-side view. See [`demos/README.md`](demos/README.md) for details.

## Documentation

```bash
make docs         # build the MkDocs site into site/
make docs-serve   # serve locally with live reload
```

The documentation site (`docs/`) includes a getting-started guide, a [coverage checklist](docs/coverage.md) of exactly what OGDF functionality is exposed, and a gallery of the demo drawings.

## How it builds

`scripts/bootstrap_ogdf.py` shallow-clones OGDF at a pinned release tag (`foxglove-202510`) into `thirdparty/ogdf` and builds its static libraries from source. The extension then links the OGDF / COIN static libraries, so wheels are self-contained. Because OGDF is prebuilt once (a couple of minutes), rebuilding the bindings only recompiles the binding sources and is fast.

The bootstrap script (`scripts/bootstrap_ogdf.py`) is cross-platform (Linux, macOS, Windows). The pin can be overridden: `python scripts/bootstrap_ogdf.py --tag <tag>` or `OGDF_TAG=<tag> make bootstrap`. In CI, run the bootstrap once per platform (e.g. in `cibuildwheel`'s `CIBW_BEFORE_ALL`) so OGDF is reused across all Python versions.
