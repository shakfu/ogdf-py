# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

- Reproducible OGDF dependency: `scripts/bootstrap_ogdf.sh` shallow-clones OGDF at a pinned tag (`foxglove-202510`) and builds its static libraries from source; the extension links them. `make build`/`make sync` auto-bootstrap if needed. Replaces reliance on a manually placed OGDF checkout.

- Persist the CMake build directory so only the bindings recompile on edits.

### Fixed

- `make build` targeted the wrong package name (`ogdf` vs `ogdf-py`), making it a silent no-op; it now rebuilds correctly.

- The generic `write` now raises `ValueError` for attribute-incapable formats (e.g. LEDA, Chaco) instead of crashing the interpreter.

## [0.1.0] - 2026-07-06

### Added

- Initial project structure

- Core module with example functions

- Test suite with pytest

- Build system using scikit-build-core
