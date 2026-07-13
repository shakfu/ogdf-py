# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0]

### Added

- Planar layouts: `FPPLayout`, `PlanarStraightLayout`, `PlanarDrawLayout`, and `MixedModelLayout` - straight-line and mixed-model planar grid drawings, completing the planar-drawing family alongside `SchnyderLayout`. Each validates that the input is a simple planar graph with at least 3 nodes.

- Shortest paths: `a_star_search`, point-to-point A* with an optional admissible heuristic; returns the path length and edges, or `None` if the target is unreachable.

- Crossing minimization: `crossing_number` (heuristic minimum crossings via the subgraph planarizer) and `insert_edges` (routes a chosen set of edges through the otherwise-planar rest of the graph and returns, per edge, the original edges it crosses).

- Flow / cut and connectivity: `min_st_cut` (directed or undirected s-t minimum cut, returning the value and the cut edges) and `node_connectivity` / `edge_connectivity` (global and local/Menger k-connectivity).

- Documentation: expanded the coverage checklist with a priority roadmap.

## [0.2.0]

### Added

- Layouts: `RadialTreeLayout`, `LinearLayout` (arc diagram), `TutteLayout` (convex planar), `DominanceLayout` / `VisibilityLayout` (upward, for DAGs), `MultilevelLayout` / `ModularMultilevelMixer` (large graphs), and `BalloonLayout`.

- Algorithms: cut vertices (`cut_vertices`) and bridges (`bridges`), Bellman-Ford shortest paths (`bellman_ford`), minimum-cost flow (`min_cost_flow`), general maximum-weight matching (`maximum_weight_matching`, Blossom V), minimum Steiner tree (`steiner_tree`, Mehlhorn), maximal planar subgraph (`maximal_planar_subgraph`), and triconnectivity via `separation_pair` and `spqr_tree_summary`.

- Cross-platform Python bootstrap (`scripts/bootstrap_ogdf.py`) replacing the bash script; generalized CMake linking (MSVC-aware); Windows build+test CI job.

- MkDocs documentation site (`docs/`) with a coverage checklist and a Gallery page rendering the demo drawings; `make docs`, `make docs-serve`, `make docs-deploy`.

- Demos: gallery entries for the new layouts, and algorithm visualizations for cut vertices/bridges, maximum-weight matching, Bellman-Ford distances, minimum-cost flow, the minimum Steiner tree, and the maximal planar subgraph.

- Generators: circulant, complete-k-partite, globe, regular-lattice; graph products (cartesian, tensor, strong, lexicographical); operations (union, complement, suspension); and random models (preferential attachment, Chung-Lu, Watts-Strogatz, Waxman, geometric-cube, hierarchy, series-parallel DAG, triconnected, planar-biconnected, planar-triconnected).

- Predicates and small algorithms: `is_two_edge_connected`, `is_regular`, `is_arborescence`, `triangulate`, `make_bimodal`, and `bfs_distances` (unweighted single-source distances).

- Windows support: the release workflow now builds Windows (AMD64) wheels alongside Linux and macOS, and the wheel matrix covers CPython 3.10-3.14.

### Fixed

- Removed the persistent CMake `build-dir` from `pyproject.toml`. Sharing it between editable installs and wheel builds could leave stale objects, so a `uv build --wheel` sometimes omitted recently-added functions. Each build now uses a fresh directory (OGDF is prebuilt, so this stays fast).

- MSVC build: replaced the non-standard `M_PI` (undefined on MSVC) with an explicit constant so the extension compiles on Windows.

## [0.1.1]

### Added

- OGDF bindings (curated subset): `Graph`/`Node`/`Edge` with iteration; `NodeArray`/`EdgeArray` in int/double/bool; `GraphAttributes` with coordinates, size, labels, and styling (colors, shapes, fill patterns, stroke, edge arrows, bends).

- Layout algorithms: `SugiyamaLayout`, `FMMMLayout`, `GEMLayout`, `SpringEmbedderKK`, `StressMinimization`, `PivotMDS`, `PlanarizationLayout` (with optional orthogonal routing), `SchnyderLayout`, `TreeLayout`, `CircularLayout`.

- Core graph algorithms: connectivity/structure predicates, connected / strong / biconnected components, topological numbering, Dijkstra shortest paths, minimum spanning tree, maximum flow, global minimum cut, matching, node coloring, and planar embedding.

- Graph generators: complete, complete-bipartite, wheel, cube, grid, Petersen, regular tree, plus random graphs, trees, digraphs, and regular / biconnected / planar variants.

- File I/O: interchange formats GML, GraphML, DOT, GEXF, GDF, TLP (with extension-based `read`/`write`) and drawing output as SVG and TikZ.

- `demos/` folder with illustrative scripts (layout gallery, styling showcase, algorithm visualizations, generator zoo, I/O round-trips) writing to `build/demo-output`; `make demos` also builds a self-contained HTML gallery (`index.html`) of every drawing.

- Bindings split into modular translation units (`bind_graph`, `bind_layouts`, `bind_algorithms`, `bind_io`, `bind_generators`).

- Auto-generated `_core.pyi` type stub for typed usage and IDE completion.

- `cibuildwheel` release workflow building CPython 3.10-3.13 wheels for Linux (x86_64, aarch64) and macOS (x86_64, arm64) on native runners, bootstrapping OGDF once per platform; trusted-publishing jobs for TestPyPI/PyPI on tags.

- CMake auto-bootstraps OGDF if missing, so `pip install` from an sdist works without a manual step (Unix only).

### Changed

- Reproducible OGDF dependency: `scripts/bootstrap_ogdf.py` (cross-platform: Linux, macOS, Windows) shallow-clones OGDF at a pinned tag (`foxglove-202510`) and builds its static libraries from source; the extension links them. `make build`/`make sync` auto-bootstrap if needed. Replaces reliance on a manually placed OGDF checkout.

- Persist the CMake build directory so only the bindings recompile on edits.

### Fixed

- `make build` targeted the wrong package name (`ogdf` vs `ogdf-py`), making it a silent no-op; it now rebuilds correctly.

- The generic `write` now raises `ValueError` for attribute-incapable formats (e.g. LEDA, Chaco) instead of crashing the interpreter.

## [0.1.0]

### Added

- Initial project structure

- Core module with example functions

- Test suite with pytest

- Build system using scikit-build-core
